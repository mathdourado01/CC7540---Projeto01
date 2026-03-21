import streamlit as st

from services.supabase_client import get_supabase_client


@st.cache_data(ttl=60, show_spinner=False)
def get_group_subjects(group_id: str, access_token: str, refresh_token: str) -> list[dict]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("group_subjects")
        .select("id, name, created_at")
        .eq("group_id", group_id)
        .order("name")
        .execute()
    )

    return response.data or []


def create_group_subject(
    group_id: str,
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_name: str,
) -> tuple[bool, str]:
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        (
            supabase.table("group_subjects")
            .insert(
                {
                    "group_id": group_id,
                    "name": subject_name.strip(),
                    "created_by": user_id,
                },
                returning="minimal",
            )
            .execute()
        )

        get_group_subjects.clear()
        return True, "Disciplina cadastrada com sucesso."

    except Exception as e:
        error_message = str(e).lower()

        if "duplicate key" in error_message:
            return False, "Já existe uma disciplina com esse nome neste grupo."

        return False, f"Erro ao cadastrar disciplina: {e}"
