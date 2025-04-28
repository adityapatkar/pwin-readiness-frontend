""" 
This script contains the Streamlit frontend code for the pWin.ai PDF Analysis Tool.
"""
import streamlit as st
import pandas as pd
try:
    import plotly.graph_objects as go
except ImportError:
    st.error("Missing dependency: 'plotly' is required for data visualization. Please install with 'pip install plotly'.")
    st.stop()

from frontend_utils import (
    create_gauge_chart,
    save_uploaded_files,
    create_side_by_side_gauge_charts,
)
from api_calls import call_classify_pdfs, call_evaluate_rfp_pdfs, call_readiness_score

st.set_page_config(page_title="pWin.AI", layout="wide")

# Define available document types for the dropdown - these match the backend classification
DOCUMENT_TYPES = ["RFP", "PWS", "SOW", "SOO", "RFP Response", "Past Performance", "Capabilities Statement", "Unknown", "Case Study"]

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
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

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
    # Add toast notification for confirmation
    st.toast("✅ Document classifications saved", icon="✅")
    if st.session_state.rfp_flag:
        st.toast("RFP document detected - continue to RFP Evaluation", icon="📋")
    else:
        st.toast("⚠️ No RFP document found", icon="⚠️")

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
    st.session_state.active_tab = 0
    # Don't reset temp_dir and file_paths here as they are set during processing

# Function to clear cache
def clear_cache_data():
    st.cache_data.clear()
    reset_analysis_state()
    st.session_state.analysis_requested = False
    st.session_state.submitted = False

# File upload section
with st.sidebar:
    st.subheader("pWin.ai Document Analysis")
    st.write("Assess proposal readiness with AI document analysis.")
    st.write("📋 Upload documents below:")
    
    # File upload
    uploaded_files = st.file_uploader(
        "📄 Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        key="upload_widget",
        on_change=handle_file_upload,
    )
    
    # Only enable the analyze button if files are uploaded
    submitted = st.button(
        "🔍 Analyze Documents", 
        key="submit_button", 
        disabled=not st.session_state.uploaded_files,
        on_click=request_analysis
    )
    
    # Select which APIs to call
    # with st.expander("⚙️ Analysis Options", False):
    #     st.multiselect(
    #         "Select analyses to perform:",
    #         ["Classify PDFs", "Evaluate RFP", "Readiness Score"],
    #         default=st.session_state.api_selection,
    #         key="api_selection_widget",
    #         on_change=update_api_selection,
    #     )
    st.session_state.api_selection = ["Classify PDFs", "Evaluate RFP", "Readiness Score"]
    
    st.button("🧹 Clear All Data", on_click=clear_cache_data, key="clear_cache_button")

# Main section
st.title("pWin.ai Proposal Readiness Analyzer")
st.write("Analyze your RFP documents to evaluate your readiness for creating winning proposal drafts.")
st.write("👈 Start by uploading your PDF files in the sidebar")

# Create the tabs
tab1, tab2, tab3 = st.tabs(["📋 Document Classification", "🔍 RFP Evaluation", "📊 Readiness Assessment"])

# Main processing logic - only run if analysis was explicitly requested via button
if st.session_state.uploaded_files and st.session_state.analysis_requested and st.session_state.submitted and not st.session_state.analysis_complete:
    try:
        # Only save files if we haven't already done so
        if not st.session_state.file_paths:
            with st.spinner("Processing your uploaded documents..."):
                st.session_state.temp_dir, st.session_state.file_paths = save_uploaded_files(st.session_state.uploaded_files)
                st.toast("Documents uploaded successfully", icon="📄")
    except Exception as e:
        with tab1:
            st.error(f"⚠️ Error while saving documents: {e}")
            st.toast(f"Error processing documents", icon="❌")
        st.stop()
    
    # Check if we need to run classification (either for display or as a prerequisite)
    need_classification = any(op in st.session_state.api_selection for op in ["Classify PDFs", "Evaluate RFP", "Readiness Score"])
    
    # Run classification if needed
    if need_classification and not st.session_state.classification_results:
        try:
            with st.spinner("AI is analyzing and classifying your documents..."):
                st.session_state.classification_results = call_classify_pdfs(st.session_state.file_paths)
                st.toast("Document classification complete", icon="🔍")
                
                # Check for any new document types returned by the backend
                if st.session_state.classification_results:
                    backend_doc_types = set([doc["doc_type"] for doc in st.session_state.classification_results])
                    new_doc_types = [dt for dt in backend_doc_types if dt not in DOCUMENT_TYPES and dt not in st.session_state.custom_doc_types]
                    
                    # Add any new document types to our custom types list
                    if new_doc_types:
                        st.session_state.custom_doc_types.extend(new_doc_types)
                    
                    # Initial check for RFP documents
                    st.session_state.rfp_flag = "RFP" in backend_doc_types
                    if st.session_state.rfp_flag:
                        st.toast("RFP document detected", icon="📋")
                    else:
                        st.toast("No RFP document found - please classify manually", icon="⚠️")
                
        except Exception as e:
            with tab1:
                st.error(f"⚠️ Classification error: {e}")
                st.toast("Classification failed", icon="❌")
            st.stop()
    
    # Mark analysis as complete to prevent reprocessing on refresh
    st.session_state.analysis_complete = True

# Tab 1: Classification
with tab1:
    st.write("Document classification identifies the type of each uploaded document.")
    st.write(
        "We automatically classify your documents as RFP, PWS, SOW, SOO, RFP Response, Past Performance, Capabilities Statement, or other types."
    )
    
    if st.session_state.classification_results:
        # Create dataframe from json response
        df = pd.DataFrame(st.session_state.classification_results)
        
        # Handle case where 'content' column might not exist
        if 'content' in df.columns:
            df.drop(columns=["content"], inplace=True)
        
        df.rename(columns={"file_name": "File Name", "doc_type": "classification"}, inplace=True)
        
        # Only show the classification analysis header if it was selected
        if "Classify PDFs" in st.session_state.api_selection:
            st.header("Document Classification Results")
        
        # Always allow editing classifications if we have them
        st.write("Review and adjust document classifications if needed. Select the correct document type for each file.")
        
        # Create a combined list of predefined and custom document types
        all_doc_types = DOCUMENT_TYPES + [dt for dt in st.session_state.custom_doc_types if dt not in DOCUMENT_TYPES]
        
        # Use data editor with callback to update session state
        edited_df = st.data_editor(
            df,
            column_config={
                "classification": st.column_config.SelectboxColumn(
                    "Document Type",
                    help="Select the correct document type",
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
        confirm_button = st.button("✅ Confirm Classifications", on_click=confirm_classifications, key="confirm_button")
        
        # Display confirmation status
        if st.session_state.edit_confirmed:
            st.success("✓ Classifications saved successfully!")
            
            # Check if there's at least one RFP document after editing
            if not st.session_state.rfp_flag:
                st.error("❌ No RFP document found. Please classify at least one document as RFP to continue.")
            else:
                st.success("✓ RFP document detected! Continue to the 'RFP Evaluation' tab to analyze requirements coverage.")
        else:
            # Use the dataframe values to check for RFP
            if not st.session_state.rfp_flag:
                st.warning("⚠️ No RFP document detected. At least one document must be classified as RFP for further analysis.")
    else:
        st.info("👆 Upload documents using the sidebar and click 'Analyze Documents' to begin.")

# Tab 2: RFP Evaluation
with tab2:
    st.write(
        "RFP Evaluation checks if your documents cover the key elements required for a winning proposal."
    )
    
    if not st.session_state.classification_results:
        st.info("📋 First step: Upload and classify your documents in the 'Document Classification' tab.")
    elif not st.session_state.edit_confirmed:
        st.warning("⚠️ Please review and confirm your document classifications in the first tab before proceeding.")
    elif not st.session_state.rfp_flag:
        st.error("❌ No RFP document identified. Please classify at least one document as RFP in the 'Document Classification' tab.")
    elif "Evaluate RFP" in st.session_state.api_selection:
        st.header("RFP Requirements Analysis")
        
        # Only call API if we don't already have results
        if not st.session_state.rfp_evaluation_results:
            try:
                with st.spinner("Analyzing key RFP requirements and elements..."):
                    st.session_state.rfp_evaluation_results = call_evaluate_rfp_pdfs(st.session_state.classification_results)
                    
                    # Show toast notification based on result
                    if st.session_state.rfp_evaluation_results.get("requirement_met", False):
                        st.toast("All RFP requirements identified", icon="✅")
                    else:
                        st.toast("Some RFP requirements missing", icon="⚠️")
                        
            except Exception as e:
                st.error(f"⚠️ Error during RFP evaluation: {e}")
                st.toast("RFP evaluation failed", icon="❌")
                st.stop()

        readiness_flag = False
        if st.session_state.rfp_evaluation_results:
            if st.session_state.rfp_evaluation_results.get("requirement_met", False):
                st.success("✅ All key requirements identified!")
                readiness_flag = True
                
                # Get the coverage dictionary
                coverage = st.session_state.rfp_evaluation_results.get("coverage", {})
                
                # Create a visual KPI-like display for coverage
                st.subheader("RFP Elements Coverage")
                
                # Define key elements to display
                key_elements = ["scope", "objectives", "tasks", "deliverables"]
                display_names = ["Scope", "Objectives", "Tasks", "Deliverables"]
                
                # Create columns for the KPI display
                cols = st.columns(4)
                
                # Apply custom CSS for better styling
                st.markdown("""
                <style>
                .kpi-card {
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    margin-bottom: 20px;
                    height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
                .kpi-title {
                    font-size: 20px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    color: #0e1117;
                }
                .kpi-value-green {
                    font-size: 42px;
                    color: #28a745;
                    text-align: center;
                }
                .kpi-value-red {
                    font-size: 42px;
                    color: #dc3545;
                    text-align: center;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Fill columns with KPI displays
                for i, element in enumerate(key_elements):
                    with cols[i]:
                        if coverage.get(element, False):
                            st.markdown(f"""
                            <div class="kpi-card">
                                <div class="kpi-title">{display_names[i]}</div>
                                <div class="kpi-value-green">✓</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="kpi-card">
                                <div class="kpi-title">{display_names[i]}</div>
                                <div class="kpi-value-red">✗</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Replace expander with subheader and individual expanders
                st.subheader("📄 RFP Element Details")
                st.write("Documents covering scope, objectives, tasks, and deliverables:")
                st.code(st.session_state.rfp_evaluation_results.get("sow_elements_file_name", ""))
                sow_elements = st.session_state.rfp_evaluation_results.get("sow_elements", {})
                for element_key, element_value in sow_elements.items():
                    with st.expander(f"{element_key}", expanded=False):
                        st.write(element_value)
                
                st.success("✓ Your documents meet the minimum requirements. Continue to the 'Readiness Assessment' tab for a detailed score.")
            else:
                st.error(
                    "❌ Requirements incomplete. Your documents don't cover all necessary elements. Please upload additional documents that address the missing elements."
                )
                with st.expander("🔍 Detailed Analysis"):
                    st.write(st.session_state.rfp_evaluation_results)
        else:
            st.error("⚠️ RFP evaluation could not be completed. Please try again or contact support.")
    else:
        st.warning("ℹ️ The 'Evaluate RFP' option is not selected. Enable it in the Analysis Options in the sidebar.")

# Tab 3: Readiness Score
with tab3:
    st.write("Readiness Assessment provides a score that indicates how prepared you are to create a winning proposal based on your documents.")
    
    if not st.session_state.classification_results:
        st.info("📋 First step: Upload and classify your documents in the 'Document Classification' tab.")
    elif not st.session_state.edit_confirmed:
        st.warning("⚠️ Please review and confirm your document classifications in the first tab before proceeding.")
    elif not st.session_state.rfp_flag:
        st.error("❌ No RFP document identified. Please classify at least one document as RFP in the 'Document Classification' tab.")
    elif not st.session_state.rfp_evaluation_results or not st.session_state.rfp_evaluation_results.get("requirement_met", False):
        st.warning("⚠️ RFP requirements analysis must be completed successfully before calculating readiness score.")
    elif "Readiness Score" in st.session_state.api_selection:
        st.header("Proposal Readiness Score")
        
        if not st.session_state.readiness_score_results:
            try:
                with st.spinner("Calculating your proposal readiness score..."):
                    st.session_state.readiness_score_results = call_readiness_score(
                        st.session_state.classification_results, st.session_state.rfp_evaluation_results
                    )
                    
                    # Show toast notification with score
                    score = st.session_state.readiness_score_results.get("readiness_score", 0)
                    st.toast(f"Readiness Score: {score*100}%", icon="📊")
                        
            except Exception as e:
                st.error(f"⚠️ Error calculating readiness score: {e}")
                st.toast("Readiness score calculation failed", icon="❌")
                st.stop()

        if st.session_state.readiness_score_results:
            score = st.session_state.readiness_score_results.get("readiness_score", 0)
            st.plotly_chart(create_gauge_chart(score))
            
            # Replace expander with subheader and individual expanders for Score Analysis
            reasons = st.session_state.readiness_score_results.get("reason", {})
            if reasons:
                st.subheader("📊 Score Analysis")
                for reason_key, reason_value in reasons.items():
                    with st.expander(f"{reason_key}", expanded=False):
                        st.write(reason_value)
            
            # Replace expander with subheader and individual expanders for Suggestions
            if "suggestions" in st.session_state.readiness_score_results and st.session_state.readiness_score_results["suggestions"]:
                st.subheader("📈 Suggestions for Improvement")
                for suggestion_key, suggestion_value in st.session_state.readiness_score_results["suggestions"].items():
                    with st.expander(f"{suggestion_key}", expanded=False):
                        st.write(suggestion_value)

            with st.expander("📈 Detailed Scoring Breakdown", expanded=True):
                scores = st.session_state.readiness_score_results.get("section_scores", {})
                if len(scores) > 3:
                    create_side_by_side_gauge_charts(scores)
                elif "message" in st.session_state.readiness_score_results:
                    st.info(st.session_state.readiness_score_results["message"])
        else:
            st.error("⚠️ Readiness score calculation failed. Please try again or contact support.")
    else:
        st.warning("ℹ️ The 'Readiness Score' option is not selected. Enable it in the Analysis Options in the sidebar.")

# Cleanup temporary directory when the session is reset or when clearing cache
if st.session_state.temp_dir and not st.session_state.analysis_complete:
    try:
        st.session_state.temp_dir.cleanup()
        st.session_state.temp_dir = None
        st.session_state.file_paths = None
    except Exception as e:
        st.error(f"⚠️ Error cleaning up temporary files: {e}")
