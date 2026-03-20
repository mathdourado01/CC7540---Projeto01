import streamlit as st

from services.supabase_client import get_supabase_client


@st.cache_data(ttl=60, show_spinner=False)
def get_user_subjects(user_id: str, access_token: str, refresh_token: str) -> list[str]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("study_sessions")
        .select("subject_name")
        .eq("user_id", user_id)
        .order("subject_name")
        .execute()
    )

    subjects = []
    seen = set()

    for row in response.data or []:
        name = (row.get("subject_name") or "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            subjects.append(name)

    return subjects
