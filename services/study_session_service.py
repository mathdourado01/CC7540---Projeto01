from datetime import date

from services.supabase_client import get_supabase_client


def register_study_session(
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_id: str,
    studied_at: date,
    studied_minutes: int,
) -> tuple[bool, str]:
    supabase = get_supabase_client(access_token, refresh_token)

    try:
        subject_response = (
            supabase.table("group_subjects")
            .select("id, name")
            .eq("id", subject_id)
            .limit(1)
            .execute()
        )

        if not subject_response.data:
            return False, "Disciplina inválida ou não encontrada."

        subject = subject_response.data[0]

        payload = {
            "user_id": user_id,
            "subject_id": subject["id"],
            "subject_name": subject["name"],
            "studied_minutes": int(studied_minutes),
            "studied_at": studied_at.isoformat(),
        }

        (
            supabase.table("study_sessions")
            .insert(payload, returning="minimal")
            .execute()
        )

        return True, "Sessão de estudo registrada com sucesso."

    except Exception as e:
        return False, f"Erro ao registrar sessão de estudo: {e}"
