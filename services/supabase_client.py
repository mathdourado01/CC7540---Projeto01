from supabase import create_client, Client
import streamlit as st


@st.cache_resource
def get_base_supabase_client() -> Client:
    url = st.secrets["url"]
    key = st.secrets["key"]
    return create_client(url, key)



def get_supabase_client(access_token: str | None = None, refresh_token: str | None = None) -> Client:
    url = st.secrets["url"]
    key = st.secrets["key"]

    if access_token and refresh_token:
        client = create_client(url, key)
        client.auth.set_session(access_token, refresh_token)
        return client

    return get_base_supabase_client()
