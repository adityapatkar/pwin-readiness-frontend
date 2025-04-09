""" 
This script contains the Streamlit frontend code for the pWin.ai PDF Analysis Tool.
"""
import streamlit as st
import pandas as pd
try:
    import plotly.graph_objects as go
except ImportError:
    st.error("Required package 'plotly' is missing. Please install it using 'pip install plotly'.")
    st.stop()

from frontend_utils import (
    create_gauge_chart,
    save_uploaded_files,
    create_side_by_side_gauge_charts,
)
from api_calls import call_classify_pdfs, call_evaluate_rfp_pdfs, call_readiness_score

st.set_page_config(page_title="pWin.AI", layout="wide")

# Define available document types for the dropdown - these match the backend classification
DOCUMENT_TYPES = ["RFP", "PWS", "SOW", "SOO", "RFP Response", "PP", "CS", "Unknown", "Other"]

# Initialize session state variables if they don't exist
if 'classification_results' not in st.session_state:
    st.session_state.classification_results = None
if 'edited_classifications' not in st.session_state:
    st.session_state.edited_classifications = None
if 'edit_confirmed' not in st.session_state:
    st.session_state.edit_confirmed = False
if 'rfp_flag' not in st.session_state:
    st.session_state.rfp_flag = False
if 'rfp_evaluation_results' not in st.session_state:
    st.session_state.rfp_evaluation_results = None
if 'api_selection' not in st.session_state:
    st.session_state.api_selection = ["Classify PDFs", "Evaluate RFP", "Readiness Score"]
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = None
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'analysis_requested' not in st.session_state:
    st.session_state.analysis_requested = False
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'file_paths' not in st.session_state:
    st.session_state.file_paths = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'custom_doc_types' not in st.session_state:
    st.session_state.custom_doc_types = []
if 'readiness_score_results' not in st.session_state:
    st.session_state.readiness_score_results = None

# Function to update classification results from edited values
def update_classifications():
    if st.session_state.edited_classifications is not None:
        edited_df = st.session_state.edited_classifications
        
        # Check if "RFP" exists in classifications
        st.session_state.rfp_flag = "RFP" in edited_df["classification"].values
            
        # Update the classification_results with the edited values
        if st.session_state.classification_results:
            for i, row in edited_df.iterrows():
                for result in st.session_state.classification_results:
                    if result["file_name"] == row["File Name"]:
                        result["doc_type"] = row["classification"]

# Function to handle classification confirmation
def confirm_classifications():
    st.session_state.edit_confirmed = True
    update_classifications()
    # Reset any subsequent analysis results since classifications changed
    st.session_state.rfp_evaluation_results = None
    st.session_state.readiness_score_results = None

# Function to handle API selection change
def update_api_selection():
    st.session_state.api_selection = st.session_state.api_selection_widget

# Function to handle file upload
def handle_file_upload():
    if st.session_state.upload_widget:
        st.session_state.uploaded_files = st.session_state.upload_widget
    else:
        st.session_state.uploaded_files = None
        st.session_state.submitted = False
        st.session_state.analysis_requested = False
        reset_analysis_state()

# Function to handle analysis request
def request_analysis():
    st.session_state.analysis_requested = True
    st.session_state.submitted = True
    # Reset analysis state for new analysis
    reset_analysis_state()

# Function to reset analysis state when uploading new files
def reset_analysis_state():
    st.session_state.classification_results = None
    st.session_state.edited_classifications = None
    st.session_state.edit_confirmed = False
    st.session_state.rfp_flag = False
    st.session_state.rfp_evaluation_results = None
    st.session_state.readiness_score_results = None
    st.session_state.analysis_complete = False
    st.session_state.custom_doc_types = []
    # Don't reset temp_dir and file_paths here as they are set during processing

# Function to clear cache
def clear_cache_data():
    st.cache_data.clear()
    reset_analysis_state()
    st.session_state.analysis_requested = False
    st.session_state.submitted = False

# File upload section
with st.sidebar:
    st.subheader("pWin.ai PDF Analysis Tool")
    st.write("Analyze PDFs to evaluate readiness for creating proposal drafts.")
    st.write("Select the operations to perform and upload PDF files.")
    
    # File upload
    uploaded_files = st.file_uploader(
        ":closed_book: Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="upload_widget",
        on_change=handle_file_upload,
    )
    
    # Only enable the analyze button if files are uploaded
    submitted = st.button(
        "Upload and Analyze", 
        key="submit_button", 
        disabled=not st.session_state.uploaded_files,
        on_click=request_analysis
    )
    
    # Select which APIs to call
    with st.expander(":gear: Operations", True):
        st.multiselect(
            "Select Operations to Perform",
            ["Classify PDFs", "Evaluate RFP", "Readiness Score"],
            default=st.session_state.api_selection,
            key="api_selection_widget",
            on_change=update_api_selection,
        )
    
    st.button("Clear Cache", on_click=clear_cache_data, key="clear_cache_button")

# Main section
st.title("pWin.ai PDF Analysis Tool")
st.subheader("Analyze PDFs to evaluate readiness for creating proposal drafts.")
st.write(" In the sidebar, upload your PDF files and select the operations to perform.")
st.write("Operations Include:")
st.write(
    "- Classify PDFs: Classify uploaded PDFs into different categories like RFP, PWS, SOW, SOO, RFP Response, PP (Past Performance), CS (Capability Statement), etc."
)
st.write(
    "- Evaluate RFP: Evaluate if the uploaded PDFs cover the required elements (scope, objectives, tasks, deliverables)."
)
st.write("- Readiness Score: Calculate the readiness score based on the uploaded PDFs.")
st.write(
    ' The subsequent operations depend on the previous operations. If you select "Evaluate RFP" or "Readiness Score", previous operations will be performed internally. Their output would not be displayed'
)

# Main processing logic - only run if analysis was explicitly requested via button
if st.session_state.uploaded_files and st.session_state.analysis_requested and st.session_state.submitted and not st.session_state.analysis_complete:
    try:
        # Only save files if we haven't already done so
        if not st.session_state.file_paths:
            with st.spinner("Processing uploaded files..."):
                st.session_state.temp_dir, st.session_state.file_paths = save_uploaded_files(st.session_state.uploaded_files)
    except Exception as e:
        st.error(f"Error saving uploaded files: {e}")
        st.stop()
    
    # Check if we need to run classification (either for display or as a prerequisite)
    need_classification = any(op in st.session_state.api_selection for op in ["Classify PDFs", "Evaluate RFP", "Readiness Score"])
    
    # Run classification if needed
    if need_classification and not st.session_state.classification_results:
        try:
            with st.spinner("Classifying PDFs..."):
                st.session_state.classification_results = call_classify_pdfs(st.session_state.file_paths)
                
                # Check for any new document types returned by the backend
                if st.session_state.classification_results:
                    backend_doc_types = set([doc["doc_type"] for doc in st.session_state.classification_results])
                    new_doc_types = [dt for dt in backend_doc_types if dt not in DOCUMENT_TYPES and dt not in st.session_state.custom_doc_types]
                    
                    # Add any new document types to our custom types list
                    if new_doc_types:
                        st.session_state.custom_doc_types.extend(new_doc_types)
                    
                    # Initial check for RFP documents
                    st.session_state.rfp_flag = "RFP" in backend_doc_types
                
        except Exception as e:
            st.error(f"Error classifying PDFs: {e}")
            st.stop()
    
    # Mark analysis as complete to prevent reprocessing on refresh
    st.session_state.analysis_complete = True

# Display UI elements if we have results
if st.session_state.classification_results:
    # Create dataframe from json response
    df = pd.DataFrame(st.session_state.classification_results)
    
    # Handle case where 'content' column might not exist
    if 'content' in df.columns:
        df.drop(columns=["content"], inplace=True)
    
    df.rename(columns={"file_name": "File Name", "doc_type": "classification"}, inplace=True)
    
    # Only show the classification analysis header if it was selected
    if "Classify PDFs" in st.session_state.api_selection:
        st.header("Classification Analysis")
    
    # Always allow editing classifications if we have them
    st.write("You can edit document classifications below. Select from the dropdown to update each document type.")
    
    # Create a combined list of predefined and custom document types
    all_doc_types = DOCUMENT_TYPES + [dt for dt in st.session_state.custom_doc_types if dt not in DOCUMENT_TYPES]
    
    # Use data editor with callback to update session state
    edited_df = st.data_editor(
        df,
        column_config={
            "classification": st.column_config.SelectboxColumn(
                "Classification",
                help="Document classification type",
                width="medium",
                options=all_doc_types,
                required=True
            )
        },
        key="classification_editor",
        disabled=["File Name"],
        hide_index=True,
        on_change=update_classifications
    )
    
    # Store the edited dataframe in session state
    st.session_state.edited_classifications = edited_df
    
    # Add a confirm button for the edited classifications
    confirm_button = st.button("Confirm Classifications", on_click=confirm_classifications, key="confirm_button")
    
    # Display confirmation status
    if st.session_state.edit_confirmed:
        st.success("Classifications updated successfully!")
        
        # Check if there's at least one RFP document after editing
        if not st.session_state.rfp_flag:
            st.error("No RFP document found after editing. Please classify at least one document as RFP.")
            if any(op in st.session_state.api_selection for op in ["Evaluate RFP", "Readiness Score"]):
                st.stop()
    else:
        # Use the dataframe values to check for RFP
        if not st.session_state.rfp_flag:
            st.warning("No RFP document detected. Please classify at least one document as RFP and confirm.")
            if any(op in st.session_state.api_selection for op in ["Evaluate RFP", "Readiness Score"]):
                st.stop()

    # RFP Evaluation - Only proceed if confirm button is clicked
    if "Evaluate RFP" in st.session_state.api_selection and st.session_state.edit_confirmed:
        st.header("RFP Evaluation")
        
        # Only call API if we don't already have results
        if not st.session_state.rfp_evaluation_results:
            try:
                with st.spinner("Extracting Scope, Objectives, Tasks, and Deliverables..."):
                    st.session_state.rfp_evaluation_results = call_evaluate_rfp_pdfs(st.session_state.classification_results)
            except Exception as e:
                st.error(f"Error evaluating RFP: {e}")
                st.stop()

        readiness_flag = False
        if st.session_state.rfp_evaluation_results:
            if st.session_state.rfp_evaluation_results.get("requirement_met", False):
                st.success("Requirement Met!")
                readiness_flag = True
                with st.expander("SOW Elements"):
                    st.write(
                        "Files that cover scope, objectives, tasks, and deliverables:"
                    )
                    st.code(st.session_state.rfp_evaluation_results.get("sow_elements_file_name", ""))
                    sow_elements = st.session_state.rfp_evaluation_results.get("sow_elements", {})
                    for key, value in sow_elements.items():
                        st.subheader(key)
                        st.write(value)
                with st.expander("Coverage"):
                    st.write(
                        "Coverage of scope, objectives, tasks, and deliverables in each file:"
                    )
                    st.write(st.session_state.rfp_evaluation_results.get("coverage", {}))
            else:
                st.error(
                    "Requirement not met. Please upload documents that cover scope, objectives, tasks, and deliverables."
                )
                with st.expander("Error Information"):
                    st.write(st.session_state.rfp_evaluation_results)

        if not readiness_flag:
            st.error(
                "Requirement not met. Please upload documents that cover scope, objectives, tasks, and deliverables."
            )
            with st.expander("Error Information"):
                st.write(st.session_state.rfp_evaluation_results)
            if "Readiness Score" in st.session_state.api_selection:
                st.stop()

    # Readiness Score
    if "Readiness Score" in st.session_state.api_selection and st.session_state.edit_confirmed:
        st.header("Readiness Score")
        
        if not st.session_state.readiness_score_results:
            try:
                with st.spinner("Calculating Readiness Score..."):
                    if not st.session_state.rfp_evaluation_results:
                        st.session_state.rfp_evaluation_results = call_evaluate_rfp_pdfs(st.session_state.classification_results)
                    st.session_state.readiness_score_results = call_readiness_score(
                        st.session_state.classification_results, st.session_state.rfp_evaluation_results
                    )
            except Exception as e:
                st.error(f"Error calculating readiness score: {e}")
                st.stop()

        if st.session_state.readiness_score_results:
            score = st.session_state.readiness_score_results.get("readiness_score", 0)
            st.plotly_chart(create_gauge_chart(score))
            with st.expander("Readiness Score Reasons"):
                reasons = st.session_state.readiness_score_results.get("reason", {})
                for key, value in reasons.items():
                    st.subheader(key)
                    st.write(value)
            with st.expander("Section Scores"):
                scores = st.session_state.readiness_score_results.get("section_scores", {})
                if len(scores) > 3:
                    create_side_by_side_gauge_charts(scores)
                elif "message" in st.session_state.readiness_score_results:
                    st.warning(st.session_state.readiness_score_results["message"])

# Cleanup temporary directory when the session is reset or when clearing cache
if st.session_state.temp_dir and not st.session_state.analysis_complete:
    try:
        st.session_state.temp_dir.cleanup()
        st.session_state.temp_dir = None
        st.session_state.file_paths = None
    except Exception as e:
        st.error(f"Error cleaning up temporary files: {e}")
