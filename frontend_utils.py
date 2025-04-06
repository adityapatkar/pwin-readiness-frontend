""" 
This module contains utility functions for the frontend of the application.
"""

import tempfile
import os
import streamlit as st
import plotly.graph_objects as go


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


@st.cache_data
def save_uploaded_files(uploaded_files):
    """
    Save the uploaded files to a temporary directory and return the file paths
    """
    temp_dir = tempfile.TemporaryDirectory()
    file_paths = []
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
