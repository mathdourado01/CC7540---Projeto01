from datetime import date

from services.supabase_client import get_supabase_client


def register_study_session(
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_name: str,
    studied_at: date,
    studied_minutes: int,
) -> tuple[bool, str]:
    supabase = get_supabase_client(access_token, refresh_token)

    payload = {
        "user_id": user_id,
        "subject_name": subject_name.strip(),
        "studied_minutes": int(studied_minutes),
        "studied_at": studied_at.isoformat(),
    }

    try:
        (
            supabase.table("study_sessions")
            .insert(payload, returning="minimal")
            .execute()
        )
        return True, "Sessão de estudo registrada com sucesso."
    except Exception as e:
        return False, f"Erro ao registrar sessão de estudo: {e}"
