""" 
This script contains the Streamlit frontend code for the pWin.ai PDF Analysis Tool.
"""

import streamlit as st
import pandas as pd
from frontend_utils import (
    create_gauge_chart,
    save_uploaded_files,
    create_side_by_side_gauge_charts,
)
from api_calls import call_classify_pdfs, call_evaluate_rfp_pdfs, call_readiness_score

st.set_page_config(page_title="pWin.AI", layout="wide")


# File upload section
with st.sidebar:
    st.subheader("pWin.ai PDF Analysis Tool")
    st.write("Analyze PDFs to evaluate readiness for creating proposal drafts.")
    st.write("Select the operations to perform and upload PDF files.")
    with st.form(":closed_book: Files", clear_on_submit=True):
        uploaded_files = st.file_uploader(
            ":closed_book: Upload PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            key="uploaded_files",
        )
        submitted = st.form_submit_button("Upload and Analyze")
    # Select which APIs to call
    with st.expander(":gear: Operations", True):
        api_selection = st.multiselect(
            "Select Operations to Perform",
            ["Classify PDFs", "Evaluate RFP", "Readiness Score"],
            default=["Classify PDFs", "Evaluate RFP", "Readiness Score"],
        )
    clear_cache = st.button("Clear Cache", on_click=st.cache_data.clear())

# Main section
st.title("pWin.ai PDF Analysis Tool")
st.subheader("Analyze PDFs to evaluate readiness for creating proposal drafts.")
st.write(" In the sidebar, upload your PDF files and select the operations to perform.")
st.write("Operations Include:")
st.write(
    "- Classify PDFs: Classify uploaded PDFs into different categories like RFP, PWS, SOW, SOO, RFP Response, etc."
)
st.write(
    "- Evaluate RFP: Evaluate if the uploaded PDFs cover the required elements (scope, objectives, tasks, deliverables)."
)
st.write("- Readiness Score: Calculate the readiness score based on the uploaded PDFs.")
st.write(
    ' The subsequent operations depend on the previous operations. If you select "Evaluate RFP" or "Readiness Score", previous operations will be performed internally. Their output would not be displayed'
)
if uploaded_files and submitted:
    try:
        temp_dir, file_paths = save_uploaded_files(uploaded_files)
    except Exception as e:
        st.error(f"Error saving uploaded files: {e}")
        st.stop()
    classification_results = None
    rfp_evaluation_results = None
    # Classification Analysis
    if "Classify PDFs" in api_selection:
        st.header("Classification Analysis")
        try:
            with st.spinner("Classifying PDFs..."):
                classification_results = call_classify_pdfs(file_paths)
        except Exception as e:
            st.error(f"Error classifying PDFs: {e}")
            st.stop()

        rfp_flag = False
        if classification_results:
            # Create dataframe from json response
            df = pd.DataFrame(classification_results)
            df.drop(columns=["content"], inplace=True)
            df.rename(columns={"file_name": "File Name", "doc_type": "classification"}, inplace=True)
            st.dataframe(df)
            if "RFP" in df["classification"].values:
                rfp_flag = True

        if not rfp_flag:
            st.error("No RFP document found. Please upload RFP documents.")
            st.stop()
    
    # RFP Evaluation
    if "Evaluate RFP" in api_selection:
        st.header("RFP Evaluation")
        try:
            with st.spinner("Extracting Scope, Objectives, Tasks, and Deliverables..."):
                if not classification_results:
                    classification_results = call_classify_pdfs(file_paths)
                rfp_evaluation_results = call_evaluate_rfp_pdfs(classification_results)
        except Exception as e:
            st.error(f"Error evaluating RFP: {e}")
            st.stop()

        readiness_flag = False
        if rfp_evaluation_results:
            if rfp_evaluation_results["requirement_met"]:
                st.success("Requirement Met!")
                readiness_flag = True
                with st.expander("SOW Elements"):
                    st.write(
                        "Files that cover scope, objectives, tasks, and deliverables:"
                    )
                    st.code(rfp_evaluation_results["sow_elements_file_name"])
                    sow_elements = rfp_evaluation_results.get("sow_elements", {})
                    for key, value in sow_elements.items():
                        st.subheader(key)
                        st.write(value)
                with st.expander("Coverage"):
                    st.write(
                        "Coverage of scope, objectives, tasks, and deliverables in each file:"
                    )
                    st.write(rfp_evaluation_results["coverage"])
            else:
                st.error(
                    "Requirement not met. Please upload documents that cover scope, objectives, tasks, and deliverables."
                )
                with st.expander("Error Information"):
                    st.write(rfp_evaluation_results)

        if not readiness_flag:
            st.error(
                "Requirement not met. Please upload documents that cover scope, objectives, tasks, and deliverables."
            )
            with st.expander("Error Information"):
                st.write(rfp_evaluation_results)
            st.stop()

    # Readiness Score
    if "Readiness Score" in api_selection:
        st.header("Readiness Score")
        try:
            with st.spinner("Calculating Readiness Score..."):
                if not classification_results:
                    classification_results = call_classify_pdfs(file_paths)
                if not rfp_evaluation_results:
                    rfp_evaluation_results = call_evaluate_rfp_pdfs(classification_results)
                readiness_score_results = call_readiness_score(
                    classification_results, rfp_evaluation_results
                )
        except Exception as e:
            st.error(f"Error calculating readiness score: {e}")
            st.stop()

        if readiness_score_results:
            score = readiness_score_results.get("readiness_score", 0)
            st.plotly_chart(create_gauge_chart(score))
            with st.expander("Readiness Score Reasons"):
                reasons = readiness_score_results.get("reason", {})
                for key, value in reasons.items():
                    st.subheader(key)
                    st.write(value)
            with st.expander("Section Scores"):
                scores = readiness_score_results.get("section_scores", {})
                if len(scores) > 3:
                    create_side_by_side_gauge_charts(scores)
                elif "message" in readiness_score_results:
                    st.warning(readiness_score_results["message"])

    # Cleanup temporary directory
    try:
        temp_dir.cleanup()
    except Exception as e:
        st.error(f"Error cleaning up temporary files: {e}")
