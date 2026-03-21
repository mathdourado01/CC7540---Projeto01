import random
import string

import streamlit as st

from services.supabase_client import get_supabase_client


def _generate_invite_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _generate_unique_invite_code(supabase, attempts: int = 10) -> str:
    for _ in range(attempts):
        code = _generate_invite_code()
        existing = (
            supabase.table("groups")
            .select("id")
            .eq("invite_code", code)
            .limit(1)
            .execute()
        )

        if not existing.data:
            return code

    raise Exception("Não foi possível gerar um código de grupo único.")


@st.cache_data(ttl=60, show_spinner=False)
def get_user_group(user_id: str, access_token: str, refresh_token: str) -> dict | None:
    supabase = get_supabase_client(access_token, refresh_token)

    membership_response = (
        supabase.table("group_members")
        .select("group_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not membership_response.data:
        return None

    group_id = membership_response.data[0]["group_id"]

    group_response = (
        supabase.table("groups")
        .select("id, name, invite_code, owner_id, created_at")
        .eq("id", group_id)
        .limit(1)
        .execute()
    )

    if not group_response.data:
        return None

    return group_response.data[0]


def create_group(user_id: str, access_token: str, refresh_token: str, group_name: str) -> tuple[bool, str]:
    supabase = get_supabase_client(access_token, refresh_token)

    current_group = get_user_group(user_id, access_token, refresh_token)
    if current_group:
        return False, "Você já participa de um grupo."

    try:
        invite_code = _generate_unique_invite_code(supabase)

        group_response = (
            supabase.table("groups")
            .insert(
                {
                    "name": group_name.strip(),
                    "invite_code": invite_code,
                    "owner_id": user_id,
                }
            )
            .execute()
        )

        if not group_response.data:
            return False, "Não foi possível criar o grupo."

        group_id = group_response.data[0]["id"]

        (
            supabase.table("group_members")
            .insert(
                {
                    "group_id": group_id,
                    "user_id": user_id,
                }
            )
            .execute()
        )

        get_user_group.clear()
        return True, "Grupo criado com sucesso."

    except Exception as e:
        return False, f"Erro ao criar grupo: {e}"


def join_group(user_id: str, access_token: str, refresh_token: str, invite_code: str) -> tuple[bool, str]:
    supabase = get_supabase_client(access_token, refresh_token)

    current_group = get_user_group(user_id, access_token, refresh_token)
    if current_group:
        return False, "Você já participa de um grupo."

    try:
        normalized_code = invite_code.strip().upper()

        group_response = (
            supabase.table("groups")
            .select("id, name")
            .eq("invite_code", normalized_code)
            .limit(1)
            .execute()
        )

        if not group_response.data:
            return False, "Código de grupo inválido."

        group_id = group_response.data[0]["id"]

        (
            supabase.table("group_members")
            .insert(
                {
                    "group_id": group_id,
                    "user_id": user_id,
                }
            )
            .execute()
        )

        get_user_group.clear()
        return True, "Você entrou no grupo com sucesso."

    except Exception as e:
        error_message = str(e).lower()

        if "duplicate key" in error_message:
            return False, "Você já participa de um grupo."

        return False, f"Erro ao entrar no grupo: {e}"
