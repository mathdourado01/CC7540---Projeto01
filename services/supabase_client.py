from supabase import create_client, Client
import streamlit as st


def get_supabase_client() -> Client:
    url = st.secrets["url"]
    key = st.secrets["key"]
    return create_client(url, key)
