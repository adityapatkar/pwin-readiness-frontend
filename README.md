# pWin.ai Frontend

This directory contains the Streamlit-based frontend for the pWin.ai PDF Analysis Tool.

## Overview

- Provides a user-friendly interface to upload and analyze PDF files.
- Integrates with backend APIs to classify documents, evaluate RFPs, and calculate readiness scores.

## Setup

1. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure proper configuration of API endpoints in the `api_calls.py` module. Export an environment variable BACKEND_URL with the base URL of the backend API.

## Usage

- Run the frontend with:
  ```bash
  streamlit run app.py
  ```
- Use the sidebar to upload PDF files and select operations.

## File Structure

- `app.py`: Main Streamlit application.
- `frontend_utils.py`: Utility functions for chart creation and file handling.
- `api_calls.py`: Module for connecting to backend APIs.
