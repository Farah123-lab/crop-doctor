# api_key.py - find the Gemini API key safely

import os

import streamlit as st


def get_api_key():
    # First: look in the computer environment
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()

    # Second: look in Streamlit secrets (used when the app is online)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass

    # Third: look in a file called key.txt
    if os.path.exists("key.txt"):
        with open("key.txt", encoding="utf-8") as file:
            return file.read().strip()

    # No key found
    return None
