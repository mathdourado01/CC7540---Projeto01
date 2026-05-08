from datetime import date, datetime
from uuid import uuid4

from services.supabase_client import get_supabase_client

from rules.gamification_rules import (
    POINTS_PER_LEVEL,
    calculate_level,
    calculate_points_to_next_level,
    calculate_current_level_progress,
)

POINTS_PER_LEVEL = 100

def build_gamification_event_key(
    event_type: str,
    source_type: str | None = None,
    source_id: str | None = None,
) -> str:
    """
    Cria uma chave única para um evento de gamificação.

    Essa chave é usada para impedir que o mesmo evento some pontos mais de uma vez.
    Para sessões de estudo, o formato esperado será algo como:

    study_session_completed:study_session:ID_DA_SESSAO
    """

    if source_type and source_id:
        return f"{event_type}:{source_type}:{source_id}"

    return f"{event_type}:manual:{uuid4()}"


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default

        return int(value)
    except (TypeError, ValueError):
        return default


def _make_json_safe(value):
    """
    Converte valores para formatos seguros para JSON/JSONB.
    """

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]

    if isinstance(value, set):
        return [_make_json_safe(item) for item in value]

    return value


def normalize_user_gamification_state(row: dict | None, user_id: str | None = None) -> dict:
    """
    Normaliza uma linha da tabela user_gamification.
    """

    row = row or {}

    total_points = _safe_int(row.get("total_points"), 0)
    level = _safe_int(row.get("level"), calculate_level(total_points))

    return {
        "user_id": row.get("user_id") or user_id,
        "total_points": total_points,
        "level": level,
        "unlocked_achievements_count": _safe_int(
            row.get("unlocked_achievements_count"),
            0,
        ),
        "last_event_key": row.get("last_event_key"),
        "last_points_delta": _safe_int(row.get("last_points_delta"), 0),
        "last_level_up_at": row.get("last_level_up_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "points_to_next_level": calculate_points_to_next_level(total_points),
        "current_level_progress": calculate_current_level_progress(total_points),
    }


def normalize_gamification_event(row: dict | None) -> dict | None:
    """
    Normaliza uma linha da tabela gamification_events.
    """

    if not row:
        return None

    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "event_key": row.get("event_key"),
        "event_type": row.get("event_type"),
        "source_type": row.get("source_type"),
        "source_id": row.get("source_id"),
        "points_delta": _safe_int(row.get("points_delta"), 0),
        "level_before": _safe_int(row.get("level_before"), 1),
        "level_after": _safe_int(row.get("level_after"), 1),
        "level_up": _safe_int(row.get("level_after"), 1) > _safe_int(row.get("level_before"), 1),
        "total_points_before": _safe_int(row.get("total_points_before"), 0),
        "total_points_after": _safe_int(row.get("total_points_after"), 0),
        "unlocked_achievement_ids": row.get("unlocked_achievement_ids") or [],
        "metadata": row.get("metadata") or {},
        "processed_at": row.get("processed_at"),
        "created_at": row.get("created_at"),
    }


def normalize_applied_event_result(row: dict | None) -> dict:
    """
    Normaliza o retorno da função RPC apply_gamification_event.
    """

    row = row or {}

    total_points = _safe_int(row.get("user_total_points"), 0)
    user_level = _safe_int(row.get("user_level"), calculate_level(total_points))

    return {
        "success": bool(row.get("success", False)),
        "already_processed": bool(row.get("already_processed", False)),
        "event": {
            "id": row.get("event_id"),
            "event_key": row.get("event_key"),
            "event_type": row.get("event_type"),
            "source_type": row.get("source_type"),
            "source_id": row.get("source_id"),
            "points_delta": _safe_int(row.get("points_delta"), 0),
            "level_before": _safe_int(row.get("level_before"), 1),
            "level_after": _safe_int(row.get("level_after"), 1),
            "level_up": bool(row.get("level_up", False)),
            "total_points_before": _safe_int(row.get("total_points_before"), 0),
            "total_points_after": _safe_int(row.get("total_points_after"), 0),
            "processed_at": row.get("processed_at"),
        },
        "state": {
            "user_id": None,
            "total_points": total_points,
            "level": user_level,
            "unlocked_achievements_count": _safe_int(
                row.get("user_unlocked_achievements_count"),
                0,
            ),
            "points_to_next_level": calculate_points_to_next_level(total_points),
            "current_level_progress": calculate_current_level_progress(total_points),
        },
    }

def get_user_gamification_state(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Busca o estado atual de gamificação do usuário.

    Retorna pontos, nível, quantidade de conquistas liberadas e dados auxiliares
    para exibição futura no app.
    """

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        response = (
            supabase.table("user_gamification")
            .select(
                "user_id, total_points, level, unlocked_achievements_count, "
                "last_event_key, last_points_delta, last_level_up_at, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {
                "success": True,
                "exists": False,
                "state": normalize_user_gamification_state(None, user_id=user_id),
                "message": "Estado de gamificação ainda não criado para este usuário.",
            }

        return {
            "success": True,
            "exists": True,
            "state": normalize_user_gamification_state(response.data[0], user_id=user_id),
            "message": "Estado de gamificação carregado com sucesso.",
        }

    except Exception as e:
        return {
            "success": False,
            "exists": False,
            "state": normalize_user_gamification_state(None, user_id=user_id),
            "message": f"Erro ao buscar estado de gamificação: {e}",
        }


def get_user_unlocked_achievements(
    user_id: str,
    access_token: str,
    refresh_token: str,
    limit: int | None = None,
) -> dict:
    """
    Busca as conquistas já desbloqueadas pelo usuário.

    Essa consulta serve como leitura básica da estrutura de conquistas do usuário
    e também apoia sincronizações entre user_achievements e user_gamification.
    """

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        query = (
            supabase.table("user_achievements")
            .select(
                "id, user_id, achievement_id, unlocked_at, "
                "achievements(id, code, title, description, criteria_type, "
                "criteria_value, points_reward, icon, is_active)"
            )
            .eq("user_id", user_id)
            .order("unlocked_at", desc=True)
        )

        if limit is not None:
            query = query.limit(int(limit))

        response = query.execute()

        achievements = []
        for row in response.data or []:
            achievement_data = row.get("achievements") or {}

            achievements.append(
                {
                    "user_achievement_id": row.get("id"),
                    "user_id": row.get("user_id"),
                    "achievement_id": row.get("achievement_id"),
                    "unlocked_at": row.get("unlocked_at"),
                    "id": achievement_data.get("id") or row.get("achievement_id"),
                    "code": achievement_data.get("code"),
                    "title": achievement_data.get("title"),
                    "description": achievement_data.get("description"),
                    "criteria_type": achievement_data.get("criteria_type"),
                    "criteria_value": achievement_data.get("criteria_value"),
                    "points_reward": _safe_int(achievement_data.get("points_reward"), 0),
                    "icon": achievement_data.get("icon"),
                    "is_active": achievement_data.get("is_active"),
                }
            )

        return {
            "success": True,
            "achievements": achievements,
            "total": len(achievements),
            "message": "Conquistas do usuário carregadas com sucesso.",
        }

    except Exception as e:
        return {
            "success": False,
            "achievements": [],
            "total": 0,
            "message": f"Erro ao buscar conquistas do usuário: {e}",
        }


def calculate_achievement_points_snapshot(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Calcula um retrato dos pontos que o usuário deveria ter com base nas
    conquistas já existentes em user_achievements.
    """

    achievements_result = get_user_unlocked_achievements(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not achievements_result.get("success"):
        return {
            "success": False,
            "total_points": 0,
            "unlocked_achievements_count": 0,
            "achievement_ids": [],
            "achievements": [],
            "message": achievements_result.get(
                "message",
                "Não foi possível calcular os pontos por conquistas.",
            ),
        }

    achievements = achievements_result.get("achievements", [])
    total_points = sum(_safe_int(achievement.get("points_reward"), 0) for achievement in achievements)

    return {
        "success": True,
        "total_points": total_points,
        "level": calculate_level(total_points),
        "unlocked_achievements_count": len(achievements),
        "achievement_ids": [
            achievement.get("achievement_id") or achievement.get("id")
            for achievement in achievements
            if achievement.get("achievement_id") or achievement.get("id")
        ],
        "achievements": achievements,
        "message": "Snapshot de pontos por conquistas calculado com sucesso.",
    }


def calculate_pending_gamification_delta_from_achievements(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Compara os pontos esperados por conquistas com os pontos persistidos em
    user_gamification.

    Essa função ajuda a recuperar casos em que uma conquista foi salva em
    user_achievements, mas o evento de gamificação ainda não foi aplicado.
    """

    state_result = get_user_gamification_state(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    snapshot_result = calculate_achievement_points_snapshot(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not snapshot_result.get("success"):
        return {
            "success": False,
            "points_delta": 0,
            "achievements_count_delta": 0,
            "achievement_ids_for_delta": [],
            "message": snapshot_result.get("message"),
        }

    current_state = state_result.get("state", {})
    stored_total_points = _safe_int(current_state.get("total_points"), 0)
    stored_achievements_count = _safe_int(
        current_state.get("unlocked_achievements_count"),
        0,
    )

    expected_total_points = _safe_int(snapshot_result.get("total_points"), 0)
    expected_achievements_count = _safe_int(
        snapshot_result.get("unlocked_achievements_count"),
        0,
    )

    points_delta = max(expected_total_points - stored_total_points, 0)
    achievements_count_delta = max(expected_achievements_count - stored_achievements_count, 0)

    achievement_ids = snapshot_result.get("achievement_ids", [])
    achievement_ids_for_delta = achievement_ids[:achievements_count_delta]

    return {
        "success": True,
        "points_delta": points_delta,
        "achievements_count_delta": achievements_count_delta,
        "achievement_ids_for_delta": achievement_ids_for_delta,
        "expected_total_points": expected_total_points,
        "stored_total_points": stored_total_points,
        "expected_achievements_count": expected_achievements_count,
        "stored_achievements_count": stored_achievements_count,
        "message": "Diferença pendente de gamificação calculada com sucesso.",
    }


def ensure_user_gamification_state(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Garante que o usuário tenha uma linha em user_gamification.

    Se ainda não existir, cria uma linha inicial. Caso o usuário já tenha
    conquistas antigas, a linha inicial já nasce com os pontos dessas conquistas.
    """

    current_state_result = get_user_gamification_state(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if current_state_result.get("success") and current_state_result.get("exists"):
        return current_state_result

    supabase = get_supabase_client(access_token, refresh_token)

    snapshot_result = calculate_achievement_points_snapshot(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    total_points = _safe_int(snapshot_result.get("total_points"), 0)
    unlocked_achievements_count = _safe_int(
        snapshot_result.get("unlocked_achievements_count"),
        0,
    )

    payload = {
        "user_id": user_id,
        "total_points": total_points,
        "level": calculate_level(total_points),
        "unlocked_achievements_count": unlocked_achievements_count,
        "last_event_key": "initial_state_from_python_service",
        "last_points_delta": 0,
    }

    try:
        response = (
            supabase.table("user_gamification")
            .insert(payload)
            .execute()
        )

        created_state = response.data[0] if response.data else payload

        return {
            "success": True,
            "exists": True,
            "state": normalize_user_gamification_state(created_state, user_id=user_id),
            "message": "Estado de gamificação criado com sucesso.",
        }

    except Exception:
        return get_user_gamification_state(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )


def get_gamification_event_by_key(
    user_id: str,
    access_token: str,
    refresh_token: str,
    event_key: str,
) -> dict:
    """
    Busca um evento de gamificação pela chave única.
    """

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        response = (
            supabase.table("gamification_events")
            .select(
                "id, user_id, event_key, event_type, source_type, source_id, "
                "points_delta, level_before, level_after, total_points_before, "
                "total_points_after, unlocked_achievement_ids, metadata, "
                "processed_at, created_at"
            )
            .eq("user_id", user_id)
            .eq("event_key", event_key)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {
                "success": True,
                "exists": False,
                "event": None,
                "message": "Evento de gamificação não encontrado.",
            }

        return {
            "success": True,
            "exists": True,
            "event": normalize_gamification_event(response.data[0]),
            "message": "Evento de gamificação encontrado.",
        }

    except Exception as e:
        return {
            "success": False,
            "exists": False,
            "event": None,
            "message": f"Erro ao buscar evento de gamificação: {e}",
        }


def get_recent_gamification_events(
    user_id: str,
    access_token: str,
    refresh_token: str,
    limit: int = 10,
) -> dict:
    """
    Busca os eventos recentes de gamificação do usuário.
    """

    supabase = get_supabase_client(access_token, refresh_token)

    try:
        response = (
            supabase.table("gamification_events")
            .select(
                "id, user_id, event_key, event_type, source_type, source_id, "
                "points_delta, level_before, level_after, total_points_before, "
                "total_points_after, unlocked_achievement_ids, metadata, "
                "processed_at, created_at"
            )
            .eq("user_id", user_id)
            .order("processed_at", desc=True)
            .limit(int(limit))
            .execute()
        )

        events = [
            normalize_gamification_event(row)
            for row in response.data or []
        ]

        return {
            "success": True,
            "events": events,
            "total": len(events),
            "message": "Eventos recentes de gamificação carregados com sucesso.",
        }

    except Exception as e:
        return {
            "success": False,
            "events": [],
            "total": 0,
            "message": f"Erro ao buscar eventos de gamificação: {e}",
        }


def apply_gamification_event(
    access_token: str,
    refresh_token: str,
    event_key: str,
    event_type: str,
    source_type: str | None = None,
    source_id: str | None = None,
    points_delta: int = 0,
    unlocked_achievement_ids: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Aplica um evento de gamificação usando a RPC do Supabase.

    Essa função é a principal camada de atualização de pontos e nível.
    A duplicidade é evitada no banco por user_id + event_key.
    """

    supabase = get_supabase_client(access_token, refresh_token)

    safe_points_delta = max(_safe_int(points_delta, 0), 0)
    safe_achievement_ids = unlocked_achievement_ids or []
    safe_metadata = _make_json_safe(metadata or {})

    try:
        response = (
            supabase.rpc(
                "apply_gamification_event",
                {
                    "p_event_key": event_key,
                    "p_event_type": event_type,
                    "p_source_type": source_type,
                    "p_source_id": source_id,
                    "p_points_delta": safe_points_delta,
                    "p_unlocked_achievement_ids": safe_achievement_ids,
                    "p_metadata": safe_metadata,
                },
            )
            .execute()
        )

        if not response.data:
            return {
                "success": False,
                "already_processed": False,
                "event": None,
                "state": None,
                "message": "A função de gamificação não retornou dados.",
            }

        normalized_result = normalize_applied_event_result(response.data[0])
        normalized_result["message"] = (
            "Evento de gamificação já havia sido processado."
            if normalized_result.get("already_processed")
            else "Evento de gamificação aplicado com sucesso."
        )

        return normalized_result

    except Exception as e:
        return {
            "success": False,
            "already_processed": False,
            "event": None,
            "state": None,
            "message": f"Erro ao aplicar evento de gamificação: {e}",
        }


def apply_study_session_gamification_event(
    user_id: str,
    access_token: str,
    refresh_token: str,
    session_id: str,
    points_delta: int,
    unlocked_achievement_ids: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Aplica o evento de gamificação referente a uma sessão de estudo.

    O event_key é baseado no ID da sessão para garantir que a mesma sessão
    nunca some pontos duas vezes.
    """

    if not session_id:
        return {
            "success": False,
            "already_processed": False,
            "event": None,
            "state": None,
            "message": "ID da sessão não informado para o evento de gamificação.",
        }

    ensure_result = ensure_user_gamification_state(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not ensure_result.get("success"):
        return {
            "success": False,
            "already_processed": False,
            "event": None,
            "state": None,
            "message": ensure_result.get(
                "message",
                "Não foi possível preparar o estado de gamificação do usuário.",
            ),
        }

    event_type = "study_session_completed"
    source_type = "study_session"
    event_key = build_gamification_event_key(
        event_type=event_type,
        source_type=source_type,
        source_id=session_id,
    )

    return apply_gamification_event(
        access_token=access_token,
        refresh_token=refresh_token,
        event_key=event_key,
        event_type=event_type,
        source_type=source_type,
        source_id=session_id,
        points_delta=points_delta,
        unlocked_achievement_ids=unlocked_achievement_ids or [],
        metadata=metadata or {},
    )