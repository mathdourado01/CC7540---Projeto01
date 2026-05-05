from datetime import date, datetime, timezone

from services.supabase_client import get_supabase_client


def _parse_study_date(value: date | str | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def _normalize_study_session(row: dict | None) -> dict | None:
    if not row:
        return None

    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "subject_id": row.get("subject_id"),
        "subject_name": row.get("subject_name"),
        "studied_minutes": row.get("studied_minutes"),
        "studied_at": row.get("studied_at"),
        "client_request_id": row.get("client_request_id"),
        "gamification_processed_at": row.get("gamification_processed_at"),
        "created_at": row.get("created_at"),
    }


def get_study_session_by_processing_key(
    user_id: str,
    access_token: str,
    refresh_token: str,
    processing_key: str,
) -> dict | None:
    """
    Busca uma sessão já registrada com a mesma chave de processamento.

    Essa busca é usada como mecanismo de idempotência: se a aplicação tentar
    reenviar o mesmo registro após queda de conexão, o sistema encontra a sessão
    original em vez de criar uma nova linha duplicada em study_sessions.
    """

    if not processing_key:
        return None

    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("study_sessions")
        .select(
            "id, user_id, subject_id, subject_name, studied_minutes, studied_at, "
            "client_request_id, gamification_processed_at, created_at"
        )
        .eq("user_id", user_id)
        .eq("client_request_id", processing_key)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return _normalize_study_session(response.data[0])


def register_study_session_once(
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_id: str,
    studied_at: date,
    studied_minutes: int,
    processing_key: str,
) -> dict:
    """
    Registra uma sessão de estudo de forma idempotente.

    A chave processing_key deve ser gerada no momento em que o usuário envia o
    formulário. Caso a mesma requisição seja reenviada, a função retorna a sessão
    já existente e não cria outra linha no banco.

    Para a proteção ficar completa no Supabase, a tabela study_sessions precisa
    ter:
    - coluna client_request_id;
    - coluna gamification_processed_at;
    - índice único por user_id + client_request_id.
    """

    if not processing_key:
        return {
            "success": False,
            "message": "Chave de processamento não informada.",
            "status": "missing_processing_key",
            "session": None,
            "was_already_registered": False,
        }

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        existing_session = get_study_session_by_processing_key(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            processing_key=processing_key,
        )

        if existing_session:
            return {
                "success": True,
                "message": "Sessão de estudo já registrada anteriormente.",
                "status": "already_registered",
                "session": existing_session,
                "was_already_registered": True,
                "gamification_already_processed": bool(
                    existing_session.get("gamification_processed_at")
                ),
            }

        subject_response = (
            supabase.table("group_subjects")
            .select("id, name")
            .eq("id", subject_id)
            .limit(1)
            .execute()
        )

        if not subject_response.data:
            return {
                "success": False,
                "message": "Disciplina inválida ou não encontrada.",
                "status": "invalid_subject",
                "session": None,
                "was_already_registered": False,
            }

        subject = subject_response.data[0]
        parsed_studied_at = _parse_study_date(studied_at)

        if parsed_studied_at is None:
            return {
                "success": False,
                "message": "Data de estudo inválida.",
                "status": "invalid_date",
                "session": None,
                "was_already_registered": False,
            }

        payload = {
            "user_id": user_id,
            "subject_id": subject["id"],
            "subject_name": subject["name"],
            "studied_minutes": int(studied_minutes),
            "studied_at": parsed_studied_at.isoformat(),
            "client_request_id": processing_key,
        }

        response = supabase.table("study_sessions").insert(payload).execute()

        inserted_session = _normalize_study_session(
            response.data[0] if response.data else payload
        )

        return {
            "success": True,
            "message": "Sessão de estudo registrada com sucesso.",
            "status": "registered",
            "session": inserted_session,
            "was_already_registered": False,
            "gamification_already_processed": False,
        }

    except Exception as e:
        existing_session = get_study_session_by_processing_key(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            processing_key=processing_key,
        )

        if existing_session:
            return {
                "success": True,
                "message": "Sessão de estudo já registrada anteriormente.",
                "status": "already_registered_after_conflict",
                "session": existing_session,
                "was_already_registered": True,
                "gamification_already_processed": bool(
                    existing_session.get("gamification_processed_at")
                ),
            }

        return {
            "success": False,
            "message": f"Erro ao registrar sessão de estudo: {e}",
            "status": "database_error",
            "session": None,
            "was_already_registered": False,
        }


def mark_study_session_gamification_processed(
    session_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Marca uma sessão como já processada pela gamificação.

    Essa marcação evita que uma tentativa repetida do mesmo registro dispare
    novamente streak, conquistas e alertas visuais.
    """

    if not session_id:
        return {
            "success": False,
            "message": "ID da sessão não informado.",
            "processed_at": None,
        }

    supabase = get_supabase_client(access_token, refresh_token)
    processed_at = datetime.now(timezone.utc).isoformat()

    try:
        response = (
            supabase.table("study_sessions")
            .update({"gamification_processed_at": processed_at})
            .eq("id", session_id)
            .execute()
        )

        updated_session = _normalize_study_session(
            response.data[0] if response.data else {"id": session_id}
        )

        return {
            "success": True,
            "message": "Sessão marcada como processada pela gamificação.",
            "processed_at": processed_at,
            "session": updated_session,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Erro ao marcar gamificação como processada: {e}",
            "processed_at": None,
        }


def register_study_session(
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_id: str,
    studied_at: date,
    studied_minutes: int,
) -> tuple[bool, str]:
    """
    Mantém compatibilidade com o fluxo antigo.

    A HU5 deve usar register_study_session_once, pois ela recebe uma chave de
    processamento e impede duplicidade. Esta função permanece apenas para não
    quebrar chamadas antigas do projeto.
    """

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

        supabase.table("study_sessions").insert(payload, returning="minimal").execute()

        return True, "Sessão de estudo registrada com sucesso."

    except Exception as e:
        return False, f"Erro ao registrar sessão de estudo: {e}"