""" 
This module contains utility functions for the frontend of the application.
"""

import tempfile
import os
import streamlit as st
import plotly.graph_objects as go
from pypdf import PdfReader, PdfWriter
from io import BytesIO


def create_gauge_chart(score, update_cache=True, title="Readiness Score"):
    """
    Create a gauge chart for the given score
    """
    delta = None
    if update_cache:
        if "delta" in st.session_state:
            delta = st.session_state["delta"]
        st.session_state["delta"] = {"reference": score}
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title},
            delta=delta,
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 50], "color": "red"},
                    {"range": [50, 75], "color": "yellow"},
                    {"range": [75, 100], "color": "green"},
                ],
            },
        )
    )
    return fig


def get_total_size(uploaded_files):
    """
    Calculate the total size of uploaded files in bytes
    """
    total_size = 0
    for file in uploaded_files:
        total_size += file.size
    return total_size


def compress_pdf(input_file):
    """
    Compress a PDF file by removing images using pypdf
    
    Args:
        input_file: StreamlitUploadedFile object containing PDF data
        
    Returns:
        BytesIO: Compressed PDF data or original data if compression doesn't reduce size
    """
    # Store original position and get size
    original_pos = input_file.tell()
    input_file.seek(0, os.SEEK_END)
    original_size = input_file.tell()
    input_file.seek(0)  # Reset to beginning for processing
    
    # Keep original data
    original_data = input_file.read()
    input_file.seek(0)  # Reset again
    
    # Create a temporary file for processing
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_input:
        temp_input.write(original_data)
        temp_input_path = temp_input.name
    
    try:
        # Create a PdfWriter with the source file
        writer = PdfWriter(clone_from=temp_input_path)
        
        # Remove images to reduce file size
        writer.remove_images()
        
        # Write to BytesIO buffer
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        
        # Get compressed size and calculate ratio
        compressed_size = len(output.getbuffer())
        compression_ratio = (original_size / compressed_size) if compressed_size > 0 else 1
        
        # Reset input file position
        input_file.seek(original_pos)
        
        # Only use compressed version if it's actually smaller
        if compressed_size < original_size:
            return output
        else:
            result = BytesIO(original_data)
            return result
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_input_path):
            os.unlink(temp_input_path)


@st.cache_data
def save_uploaded_files(uploaded_files):
    """
    Save the uploaded files to a temporary directory and return the file paths
    """
    temp_dir = tempfile.TemporaryDirectory()
    file_paths = []
    
    # Check total size
    total_size = get_total_size(uploaded_files)
    size_threshold = 30 * 1024 * 1024  # 30MB in bytes
    
    # Inform user if compression will happen
    if total_size > size_threshold:
        st.warning(f"Total file size ({total_size/1048576:.2f}MB) exceeds 30MB threshold. Files will be compressed.")
        
        # Create a list of (file, size) tuples and sort by size (largest first)
        file_sizes = [(file, file.size) for file in uploaded_files]
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Process files in order of size (largest first)
        for uploaded_file, size in file_sizes:
            file_path = os.path.join(temp_dir.name, uploaded_file.name)
            
            with st.spinner(f"Compressing {uploaded_file.name} ({size/1048576:.2f}MB)..."):
                compressed_data = compress_pdf(uploaded_file)
                with open(file_path, "wb") as f:
                    f.write(compressed_data.getbuffer())
                
            file_paths.append(file_path)
    else:
        # If no compression needed, process files in original order
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir.name, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(file_path)
    
    return temp_dir, file_paths


def create_side_by_side_gauge_charts(scores):
    """
    Create side by side gauge charts for the given scores
    """
    col1, col2, col3, col4 = st.columns(4)
    fig1 = create_gauge_chart(scores.get("scope", 0), update_cache=False, title="Scope")
    fig2 = create_gauge_chart(scores.get("objectives", 0), update_cache=False, title="Objectives")
    fig3 = create_gauge_chart(scores.get("tasks", 0), update_cache=False, title="Tasks")
    fig4 = create_gauge_chart(scores.get("deliverables", 0), update_cache=False, title="Deliverables")
    with col1:
        st.plotly_chart(fig1)
    with col2:
        st.plotly_chart(fig2)
    with col3:
        st.plotly_chart(fig3)
    with col4:
        st.plotly_chart(fig4)
