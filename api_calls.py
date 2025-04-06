""" 
    This module contains the functions to call the backend APIs.
"""

import requests
import os
import streamlit as st
from constants import BASE_URL, API_KEY


@st.cache_data
def call_classify_pdfs(file_paths):
    """
    Call the classify-pdfs API to classify the given PDFs

    Args:
        file_paths (List[str]): List of file paths to classify

    Returns:
        List[Dict[str, str]]: List of dictionaries containing the file name and classification
    """
    url = f"{BASE_URL}classify/"
    files_dict = [
        (
            "files",
            (os.path.basename(file_path), open(file_path, "rb"), "application/pdf"),
        )
        for file_path in file_paths
    ]

    try:
        response = requests.post(url, files=files_dict, headers={"X-API-Key": API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling classify-pdfs API: {str(e)}")
        return None
    finally:
        for f in files_dict:
            f[1][1].close()


@st.cache_data
def call_evaluate_rfp_pdfs(classification_results):
    """
    Call the evaluate-rfp-pdfs API to evaluate the given PDFs

    Args:
        classification_results (List[Dict[str, str]]): List of dictionaries containing the file name and classification

    Returns:
        Dict[str, str] Dictionary containing the extracted content
    """
    url = f"{BASE_URL}extract/"
    try:
        response = requests.post(url, json=classification_results, headers={"X-API-Key": API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling evaluate-rfp-pdfs API: {str(e)}")
        return None


@st.cache_data
def call_readiness_score(classification_results, rfps_content):
    """
    Call the readiness_score API to get the readiness score of the given PDFs

    Args:
        classification_results (List[Dict[str, str]]): List of dictionaries containing the file name and classification
        rfps_content (Dict[str, str]): Dictionary containing the extracted content

    Returns:
        Dict[str, str] Dictionary containing the readiness score and reasons
    """
    url = f"{BASE_URL}/score/"
    request_data = {"classified_docs": classification_results, "extracted_rfp_result": rfps_content}

    try:
        response = requests.post(url, json=request_data, headers={"X-API-Key": API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling readiness_score API: {str(e)}")
        return None
