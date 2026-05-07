from copy import deepcopy
from datetime import date
from time import perf_counter
from uuid import uuid4

from services.achievement_service import (
    DEFAULT_ACHIEVEMENTS,
    check_reached_achievements,
)
from services.dashboard_service import calculate_dashboard_metrics, get_study_history
from services.gamification_state_service import (
    apply_study_session_gamification_event,
    calculate_pending_gamification_delta_from_achievements,
    ensure_user_gamification_state,
    get_recent_gamification_events,
    get_user_gamification_state,
)
from services.streak_service import (
    calculate_streak_summary_from_history,
    update_streak_after_study_session,
)
from services.study_session_service import (
    mark_study_session_gamification_processed,
    register_study_session_once,
)


def generate_processing_key() -> str:
    """
    Gera uma chave única para identificar uma tentativa de registro de sessão.

    A mesma chave deve ser reutilizada se a aplicação precisar reenviar o mesmo
    registro após queda de conexão. Assim, o banco consegue diferenciar um retry
    técnico de uma nova sessão criada intencionalmente pelo usuário.
    """

    return str(uuid4())


def _parse_study_date(value: date | str | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def _normalize_streak(streak_data: dict | None) -> dict:
    streak_data = streak_data or {}
    longest_streak = int(
        streak_data.get(
            "longest_streak",
            streak_data.get("highest_streak", 0),
        )
        or 0
    )

    return {
        "current_streak": int(streak_data.get("current_streak", 0) or 0),
        "longest_streak": longest_streak,
        "highest_streak": longest_streak,
        "last_study_date": streak_data.get("last_study_date"),
        "latest_study_date": streak_data.get(
            "latest_study_date",
            streak_data.get("last_study_date"),
        ),
        "status": streak_data.get("status"),
        "message": streak_data.get("message"),
    }


def _clear_cached_study_history() -> None:
    clear_function = getattr(get_study_history, "clear", None)

    if callable(clear_function):
        clear_function()


def _build_streak_feedback(previous_streak: dict, updated_streak: dict) -> dict:
    previous_streak = _normalize_streak(previous_streak)
    updated_streak = _normalize_streak(updated_streak)

    previous_current_streak = previous_streak.get("current_streak", 0)
    updated_current_streak = updated_streak.get("current_streak", 0)

    previous_highest_streak = previous_streak.get("highest_streak", 0)
    updated_highest_streak = updated_streak.get("highest_streak", 0)

    if (
        updated_current_streak > previous_current_streak
        and updated_highest_streak > previous_highest_streak
    ):
        return {
            "type": "success",
            "message": (
                f"🔥 Sua streak subiu para {updated_current_streak} dias e você "
                f"bateu um novo recorde de {updated_highest_streak} dias!"
            ),
        }

    if updated_current_streak > previous_current_streak:
        return {
            "type": "success",
            "message": f"🔥 Sua streak foi atualizada para {updated_current_streak} dias consecutivos!",
        }

    if updated_highest_streak > previous_highest_streak:
        return {
            "type": "success",
            "message": f"🏅 Novo recorde alcançado: {updated_highest_streak} dias consecutivos!",
        }

    if updated_current_streak < previous_current_streak:
        return {
            "type": "warning",
            "message": f"⚠️ Sua streak atual agora é de {updated_current_streak} dias.",
        }

    return {
        "type": "info",
        "message": "Seus indicadores de streak já foram atualizados com o novo registro.",
    }


def _build_empty_achievement_result(message: str | None = None) -> dict:
    return {
        "success": True,
        "unlocked_achievements": [],
        "total_unlocked": 0,
        "already_unlocked_count": 0,
        "has_new_achievements": False,
        "message": message or "Nenhuma nova conquista desbloqueada.",
    }


def _calculate_points_from_achievements(achievement_result: dict) -> int:
    return sum(
        int(achievement.get("points_reward", 0) or 0)
        for achievement in achievement_result.get("unlocked_achievements", [])
    )


def _get_achievement_ids_from_result(achievement_result: dict) -> list[str]:
    achievement_ids = []

    for achievement in achievement_result.get("unlocked_achievements", []):
        achievement_id = achievement.get("id") or achievement.get("achievement_id")

        if achievement_id:
            achievement_ids.append(str(achievement_id))

    return achievement_ids


def _normalize_gamification_state_result(state_result: dict | None) -> dict:
    state_result = state_result or {}
    state = state_result.get("state") or state_result

    return {
        "user_id": state.get("user_id"),
        "total_points": int(state.get("total_points", 0) or 0),
        "level": int(state.get("level", 1) or 1),
        "unlocked_achievements_count": int(
            state.get("unlocked_achievements_count", 0) or 0
        ),
        "last_event_key": state.get("last_event_key"),
        "last_points_delta": int(state.get("last_points_delta", 0) or 0),
        "last_level_up_at": state.get("last_level_up_at"),
        "points_to_next_level": int(state.get("points_to_next_level", 100) or 0),
        "current_level_progress": state.get("current_level_progress") or {},
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


def _normalize_gamification_event_result(event_result: dict | None) -> dict:
    event_result = event_result or {}

    return {
        "success": bool(event_result.get("success", False)),
        "already_processed": bool(event_result.get("already_processed", False)),
        "message": event_result.get("message"),
        "event": event_result.get("event"),
        "state": _normalize_gamification_state_result(event_result.get("state")),
    }


def _calculate_points_earned_now(
    achievement_result: dict,
    gamification_event_result: dict | None,
) -> int:
    event_result = gamification_event_result or {}

    if event_result.get("success") and event_result.get("event"):
        if event_result.get("already_processed"):
            return 0

        return int(event_result["event"].get("points_delta", 0) or 0)

    return _calculate_points_from_achievements(achievement_result)


def _build_gamification_metadata(
    session_result: dict,
    achievement_result: dict,
    updated_metrics: dict,
    normalized_streak: dict,
    processing_key: str,
    pending_delta_result: dict | None = None,
) -> dict:
    session_data = session_result.get("session") or {}
    pending_delta_result = pending_delta_result or {}

    return {
        "processing_key": processing_key,
        "session_status": session_result.get("status"),
        "was_already_registered": session_result.get("was_already_registered", False),
        "session": {
            "id": session_data.get("id"),
            "subject_id": session_data.get("subject_id"),
            "subject_name": session_data.get("subject_name"),
            "studied_minutes": session_data.get("studied_minutes"),
            "studied_at": session_data.get("studied_at"),
            "client_request_id": session_data.get("client_request_id"),
        },
        "achievements": {
            "has_new_achievements": achievement_result.get("has_new_achievements", False),
            "total_unlocked": achievement_result.get("total_unlocked", 0),
            "unlocked_achievement_ids": _get_achievement_ids_from_result(achievement_result),
            "unlocked_achievement_codes": [
                achievement.get("code")
                for achievement in achievement_result.get("unlocked_achievements", [])
                if achievement.get("code")
            ],
        },
        "metrics": {
            "total_sessions": updated_metrics.get("total_sessions", 0),
            "total_minutes": updated_metrics.get("total_minutes", 0),
            "total_hours": updated_metrics.get("total_hours", 0),
            "current_streak": updated_metrics.get("current_streak", 0),
            "highest_streak": updated_metrics.get("highest_streak", 0),
            "longest_streak": updated_metrics.get("longest_streak", 0),
        },
        "streak": normalized_streak,
        "pending_delta_recovery": {
            "used": bool(pending_delta_result.get("used", False)),
            "points_delta": pending_delta_result.get("points_delta", 0),
            "achievements_count_delta": pending_delta_result.get("achievements_count_delta", 0),
        },
    }


def build_fast_gamification_response(
    success: bool,
    message: str,
    processing_key: str,
    session_result: dict | None = None,
    streak_result: dict | None = None,
    achievement_result: dict | None = None,
    metrics: dict | None = None,
    dashboard_history: list[dict] | None = None,
    feedback: dict | None = None,
    gamification_state_result: dict | None = None,
    gamification_event_result: dict | None = None,
    recent_gamification_events_result: dict | None = None,
    started_at: float | None = None,
) -> dict:
    """
    Monta um retorno único e rápido para o app.

    A ideia é que o app não precise entender todos os passos internos da
    gamificação. Ele recebe um pacote pronto com sessão, streak, conquistas,
    métricas, pontos, nível, evento processado e mensagem visual imediata.
    """

    achievement_result = achievement_result or _build_empty_achievement_result()
    session_result = session_result or {}
    gamification_event_result = gamification_event_result or {}
    recent_gamification_events_result = recent_gamification_events_result or {}

    points_earned_now = _calculate_points_earned_now(
        achievement_result=achievement_result,
        gamification_event_result=gamification_event_result,
    )

    normalized_event_result = _normalize_gamification_event_result(
        gamification_event_result
    )

    if gamification_state_result:
        normalized_state = _normalize_gamification_state_result(gamification_state_result)
    else:
        normalized_state = normalized_event_result.get("state", {})

    processing_seconds = None
    if started_at is not None:
        processing_seconds = round(perf_counter() - started_at, 4)

    has_new_achievements = achievement_result.get("has_new_achievements", False)
    event_already_processed = bool(normalized_event_result.get("already_processed", False))

    should_show_visual_alert = bool(
        success
        and has_new_achievements
        and not event_already_processed
    )

    return {
        "success": success,
        "message": message,
        "processing_key": processing_key,
        "processing_seconds": processing_seconds,
        "processed_under_three_seconds": (
            processing_seconds is None or processing_seconds <= 3
        ),
        "session": session_result.get("session"),
        "session_status": session_result.get("status"),
        "was_already_registered": session_result.get("was_already_registered", False),
        "gamification_already_processed": session_result.get(
            "gamification_already_processed",
            False,
        ),
        "streak": _normalize_streak(streak_result),
        "metrics": metrics or {},
        "dashboard_history": dashboard_history or [],
        "achievements": achievement_result,
        "points_earned": points_earned_now,
        "has_new_achievements": has_new_achievements,
        "should_show_visual_alert": should_show_visual_alert,
        "gamification": {
            "state": normalized_state,
            "event": normalized_event_result.get("event"),
            "event_success": normalized_event_result.get("success", False),
            "event_already_processed": event_already_processed,
            "recent_events": recent_gamification_events_result.get("events", []),
            "total_points": normalized_state.get("total_points", 0),
            "level": normalized_state.get("level", 1),
            "points_to_next_level": normalized_state.get("points_to_next_level", 100),
            "current_level_progress": normalized_state.get("current_level_progress", {}),
            "level_up": bool(
                normalized_event_result.get("event", {}).get("level_up", False)
            )
            if normalized_event_result.get("event")
            else False,
        },
        "feedback": feedback or {
            "type": "success" if success else "error",
            "message": message,
        },
    }


def _get_fresh_dashboard_package(
    user_id: str,
    access_token: str,
    refresh_token: str,
    streak_data: dict | None = None,
) -> tuple[list[dict], dict, dict]:
    _clear_cached_study_history()

    updated_history = get_study_history(
        user_id,
        access_token,
        refresh_token,
    )

    updated_metrics = calculate_dashboard_metrics(updated_history)
    normalized_streak = _normalize_streak(streak_data)

    updated_metrics["current_streak"] = normalized_streak.get("current_streak", 0)
    updated_metrics["highest_streak"] = normalized_streak.get("highest_streak", 0)
    updated_metrics["longest_streak"] = normalized_streak.get("longest_streak", 0)
    updated_metrics["last_study_date"] = normalized_streak.get("last_study_date")

    return updated_history, updated_metrics, normalized_streak


def process_study_session_with_gamification(
    user_id: str,
    access_token: str,
    refresh_token: str,
    subject_id: str,
    studied_at: date,
    studied_minutes: int,
    processing_key: str | None = None,
    previous_streak: dict | None = None,
) -> dict:
    """
    Fluxo principal da HU5.

    Esta rotina acopla a gamificação ao salvamento da sessão:
    1. registra a sessão de forma idempotente;
    2. impede que o mesmo registro seja contabilizado duas vezes;
    3. garante/cria o estado de pontos e nível do usuário;
    4. atualiza streak;
    5. recalcula métricas necessárias para conquistas;
    6. libera conquistas novas;
    7. registra um evento único de gamificação;
    8. atualiza pontos e nível;
    9. marca a sessão como processada;
    10. devolve uma estrutura pronta para feedback imediato no Streamlit.
    """

    started_at = perf_counter()
    processing_key = processing_key or generate_processing_key()
    previous_streak = _normalize_streak(previous_streak)

    session_result = register_study_session_once(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        subject_id=subject_id,
        studied_at=studied_at,
        studied_minutes=int(studied_minutes),
        processing_key=processing_key,
    )

    if not session_result.get("success"):
        return build_fast_gamification_response(
            success=False,
            message=session_result.get("message", "Não foi possível registrar a sessão."),
            processing_key=processing_key,
            session_result=session_result,
            feedback={
                "type": "error",
                "message": session_result.get(
                    "message",
                    "Não foi possível registrar a sessão.",
                ),
            },
            started_at=started_at,
        )

    current_state_result = ensure_user_gamification_state(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not current_state_result.get("success"):
        return build_fast_gamification_response(
            success=False,
            message=current_state_result.get(
                "message",
                "Não foi possível preparar o estado de gamificação.",
            ),
            processing_key=processing_key,
            session_result=session_result,
            gamification_state_result=current_state_result,
            feedback={
                "type": "error",
                "message": current_state_result.get(
                    "message",
                    "Não foi possível preparar o estado de gamificação.",
                ),
            },
            started_at=started_at,
        )

    if session_result.get("gamification_already_processed"):
        updated_history, updated_metrics, normalized_streak = _get_fresh_dashboard_package(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            streak_data=previous_streak,
        )

        state_result = get_user_gamification_state(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        recent_events_result = get_recent_gamification_events(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            limit=5,
        )

        return build_fast_gamification_response(
            success=True,
            message="Este registro já havia sido processado anteriormente. Nenhum ponto foi duplicado.",
            processing_key=processing_key,
            session_result=session_result,
            streak_result=normalized_streak,
            achievement_result=_build_empty_achievement_result(
                "Registro já processado. Nenhuma conquista foi duplicada."
            ),
            metrics=updated_metrics,
            dashboard_history=updated_history,
            gamification_state_result=state_result,
            recent_gamification_events_result=recent_events_result,
            feedback={
                "type": "info",
                "message": "Este registro já havia sido processado anteriormente. Nenhum ponto foi duplicado.",
            },
            started_at=started_at,
        )

    updated_streak = update_streak_after_study_session(
        user_id=user_id,
        studied_at=studied_at,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    updated_history, updated_metrics, normalized_streak = _get_fresh_dashboard_package(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        streak_data=updated_streak,
    )

    achievement_result = check_reached_achievements(
        user_id=user_id,
        metrics=updated_metrics,
        streak_data=normalized_streak,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    points_earned_from_new_achievements = _calculate_points_from_achievements(
        achievement_result
    )
    unlocked_achievement_ids = _get_achievement_ids_from_result(achievement_result)

    pending_delta_result = {
        "used": False,
        "points_delta": 0,
        "achievements_count_delta": 0,
        "achievement_ids_for_delta": [],
    }

    points_delta_to_apply = points_earned_from_new_achievements
    achievement_ids_to_apply = unlocked_achievement_ids

    if points_delta_to_apply <= 0:
        pending_delta_result = calculate_pending_gamification_delta_from_achievements(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        if (
            pending_delta_result.get("success")
            and pending_delta_result.get("points_delta", 0) > 0
        ):
            pending_delta_result["used"] = True
            points_delta_to_apply = int(pending_delta_result.get("points_delta", 0) or 0)
            achievement_ids_to_apply = pending_delta_result.get(
                "achievement_ids_for_delta",
                [],
            )

    session_data = session_result.get("session") or {}
    session_id = session_data.get("id")

    gamification_metadata = _build_gamification_metadata(
        session_result=session_result,
        achievement_result=achievement_result,
        updated_metrics=updated_metrics,
        normalized_streak=normalized_streak,
        processing_key=processing_key,
        pending_delta_result=pending_delta_result,
    )

    gamification_event_result = apply_study_session_gamification_event(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        session_id=session_id,
        points_delta=points_delta_to_apply,
        unlocked_achievement_ids=achievement_ids_to_apply,
        metadata=gamification_metadata,
    )

    if not gamification_event_result.get("success"):
        return build_fast_gamification_response(
            success=False,
            message=gamification_event_result.get(
                "message",
                "A sessão foi registrada, mas não foi possível aplicar o evento de gamificação.",
            ),
            processing_key=processing_key,
            session_result=session_result,
            streak_result=normalized_streak,
            achievement_result=achievement_result,
            metrics=updated_metrics,
            dashboard_history=updated_history,
            gamification_state_result=current_state_result,
            gamification_event_result=gamification_event_result,
            feedback={
                "type": "warning",
                "message": gamification_event_result.get(
                    "message",
                    "A sessão foi registrada, mas não foi possível aplicar o evento de gamificação.",
                ),
            },
            started_at=started_at,
        )

    mark_result = mark_study_session_gamification_processed(
        session_id=session_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not mark_result.get("success"):
        return build_fast_gamification_response(
            success=False,
            message=mark_result.get(
                "message",
                "A sessão foi registrada, mas não foi possível finalizar a marcação de gamificação.",
            ),
            processing_key=processing_key,
            session_result=session_result,
            streak_result=normalized_streak,
            achievement_result=achievement_result,
            metrics=updated_metrics,
            dashboard_history=updated_history,
            gamification_state_result=current_state_result,
            gamification_event_result=gamification_event_result,
            feedback={
                "type": "warning",
                "message": mark_result.get(
                    "message",
                    "A sessão foi registrada, mas não foi possível finalizar a marcação de gamificação.",
                ),
            },
            started_at=started_at,
        )

    final_state_result = get_user_gamification_state(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    recent_events_result = get_recent_gamification_events(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        limit=5,
    )

    feedback = _build_streak_feedback(previous_streak, normalized_streak)

    event_already_processed = bool(gamification_event_result.get("already_processed", False))
    level_up = bool(
        (gamification_event_result.get("event") or {}).get("level_up", False)
    )

    if achievement_result.get("has_new_achievements") and not event_already_processed:
        total_unlocked = achievement_result.get("total_unlocked", 0)
        feedback = {
            "type": "success",
            "message": (
                f"🏆 {total_unlocked} nova(s) conquista(s) desbloqueada(s)! "
                f"+{points_delta_to_apply} pontos."
            ),
        }

    if level_up and not event_already_processed:
        new_level = (gamification_event_result.get("event") or {}).get("level_after")
        feedback = {
            "type": "success",
            "message": f"🚀 Você subiu para o nível {new_level}! Continue mantendo o ritmo.",
        }

    if event_already_processed:
        feedback = {
            "type": "info",
            "message": "Este evento de gamificação já havia sido processado. Nenhum ponto foi duplicado.",
        }

    return build_fast_gamification_response(
        success=True,
        message="Sessão registrada e gamificação processada com sucesso.",
        processing_key=processing_key,
        session_result=session_result,
        streak_result=normalized_streak,
        achievement_result=achievement_result,
        metrics=updated_metrics,
        dashboard_history=updated_history,
        gamification_state_result=final_state_result,
        gamification_event_result=gamification_event_result,
        recent_gamification_events_result=recent_events_result,
        feedback=feedback,
        started_at=started_at,
    )


def _prepare_simulated_achievements(achievements: list[dict] | None = None) -> list[dict]:
    source = achievements or DEFAULT_ACHIEVEMENTS
    prepared_achievements = []

    for index, achievement in enumerate(source, start=1):
        prepared = deepcopy(achievement)
        prepared["id"] = prepared.get("id") or prepared.get("code") or f"achievement_{index}"
        prepared["points_reward"] = int(prepared.get("points_reward", 0) or 0)
        prepared["criteria_value"] = int(prepared.get("criteria_value", 0) or 0)
        prepared_achievements.append(prepared)

    return prepared_achievements


def _calculate_simulated_level(total_points: int) -> int:
    return max((int(total_points or 0) // 100) + 1, 1)


def _calculate_simulated_points_to_next_level(total_points: int) -> int:
    total_points = int(total_points or 0)
    current_level = _calculate_simulated_level(total_points)
    next_level_minimum_points = current_level * 100

    return max(next_level_minimum_points - total_points, 0)


def _calculate_simulated_level_progress(total_points: int) -> dict:
    total_points = int(total_points or 0)
    current_level = _calculate_simulated_level(total_points)
    current_level_minimum_points = (current_level - 1) * 100
    points_inside_level = total_points - current_level_minimum_points

    return {
        "current_level": current_level,
        "points_inside_level": points_inside_level,
        "points_required_in_level": 100,
        "progress_percentage": min(round((points_inside_level / 100) * 100, 2), 100),
    }


def _calculate_simulated_metrics(history: list[dict], reference_date: date | None = None) -> dict:
    streak_summary = calculate_streak_summary_from_history(
        history,
        reference_date=reference_date,
    )

    total_sessions = len(history)
    total_minutes = sum(int(item.get("studied_minutes", 0) or 0) for item in history)

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "current_streak": streak_summary.get("current_streak", 0),
        "highest_streak": streak_summary.get("highest_streak", 0),
        "longest_streak": streak_summary.get("longest_streak", 0),
        "last_study_date": streak_summary.get("last_study_date"),
        "latest_study_date": streak_summary.get("latest_study_date"),
    }


def _get_simulated_metric_value(achievement: dict, metrics: dict) -> int:
    criteria_type = achievement.get("criteria_type")

    if criteria_type == "longest_streak":
        return int(metrics.get("longest_streak", metrics.get("highest_streak", 0)) or 0)

    return int(metrics.get(criteria_type, 0) or 0)


def _check_simulated_achievements(
    achievements: list[dict],
    unlocked_codes: set[str],
    metrics: dict,
) -> list[dict]:
    newly_unlocked = []

    for achievement in achievements:
        code = achievement.get("code")

        if code in unlocked_codes:
            continue

        current_value = _get_simulated_metric_value(achievement, metrics)
        target_value = int(achievement.get("criteria_value", 0) or 0)

        if current_value >= target_value:
            newly_unlocked.append(
                {
                    "id": achievement.get("id"),
                    "code": code,
                    "title": achievement.get("title"),
                    "description": achievement.get("description"),
                    "criteria_type": achievement.get("criteria_type"),
                    "criteria_value": target_value,
                    "points_reward": int(achievement.get("points_reward", 0) or 0),
                    "icon": achievement.get("icon"),
                }
            )
            unlocked_codes.add(code)

    return newly_unlocked


def simulate_gamification_batches(
    test_batches: list[dict],
    achievements: list[dict] | None = None,
    default_reference_date: date | str | None = None,
) -> list[dict]:
    """
    Simula múltiplos registros de estudo sem acessar o Supabase.

    Uso esperado nos testes internos:
    - validar se registros duplicados, com a mesma processing_key, não geram
      sessões/pontos/conquistas duplicadas;
    - validar se várias sessões liberam conquistas na ordem correta;
    - validar se o retorno rápido do processamento contém os dados necessários
      para exibição imediata no app;
    - validar evolução de pontos, nível e eventos únicos.
    """

    prepared_achievements = _prepare_simulated_achievements(achievements)
    parsed_default_reference_date = _parse_study_date(default_reference_date)
    batch_results = []

    for batch_index, batch in enumerate(test_batches, start=1):
        batch_name = batch.get("name") or f"Lote {batch_index}"
        records = batch.get("records", [])
        expected = batch.get("expected", {})

        history = []
        processed_keys = set()
        processed_event_keys = set()
        unlocked_codes = set()
        total_points = 0
        current_level = 1
        record_results = []

        for record_index, record in enumerate(records, start=1):
            processing_key = record.get("processing_key") or f"{batch_name}_{record_index}"
            studied_at = _parse_study_date(record.get("studied_at"))
            reference_date = _parse_study_date(record.get("reference_date"))

            if reference_date is None:
                reference_date = parsed_default_reference_date

            event_key = f"study_session_completed:study_session:{processing_key}"

            if processing_key in processed_keys or event_key in processed_event_keys:
                metrics = _calculate_simulated_metrics(history, reference_date=reference_date)

                record_results.append(
                    {
                        "record_index": record_index,
                        "processing_key": processing_key,
                        "event_key": event_key,
                        "status": "duplicated",
                        "processed": False,
                        "message": "Registro ignorado porque a chave de processamento já foi usada.",
                        "metrics": metrics,
                        "unlocked_achievements": [],
                        "points_earned": 0,
                        "total_points": total_points,
                        "level": current_level,
                        "points_to_next_level": _calculate_simulated_points_to_next_level(total_points),
                        "current_level_progress": _calculate_simulated_level_progress(total_points),
                        "feedback": {
                            "type": "info",
                            "message": "Registro duplicado ignorado. Nenhum ponto foi duplicado.",
                        },
                    }
                )
                continue

            processed_keys.add(processing_key)
            processed_event_keys.add(event_key)

            history.append(
                {
                    "id": processing_key,
                    "subject_id": record.get("subject_id"),
                    "subject_name": record.get("subject_name", "Disciplina simulada"),
                    "studied_minutes": int(record.get("studied_minutes", 0) or 0),
                    "studied_at": studied_at.isoformat() if studied_at is not None else None,
                    "client_request_id": processing_key,
                }
            )

            metrics = _calculate_simulated_metrics(history, reference_date=reference_date)
            newly_unlocked = _check_simulated_achievements(
                achievements=prepared_achievements,
                unlocked_codes=unlocked_codes,
                metrics=metrics,
            )

            points_earned = sum(
                int(achievement.get("points_reward", 0) or 0)
                for achievement in newly_unlocked
            )

            level_before = current_level
            points_before = total_points
            total_points += points_earned
            current_level = _calculate_simulated_level(total_points)
            level_up = current_level > level_before

            has_new_achievements = len(newly_unlocked) > 0

            if level_up:
                feedback = {
                    "type": "success",
                    "message": f"🚀 Subiu para o nível {current_level}! +{points_earned} pontos.",
                }
            elif has_new_achievements:
                feedback = {
                    "type": "success",
                    "message": f"{len(newly_unlocked)} conquista(s) desbloqueada(s). +{points_earned} pontos.",
                }
            else:
                feedback = {
                    "type": "info",
                    "message": "Registro salvo sem novas conquistas.",
                }

            record_results.append(
                {
                    "record_index": record_index,
                    "processing_key": processing_key,
                    "event_key": event_key,
                    "status": "processed",
                    "processed": True,
                    "message": "Registro processado pela gamificação.",
                    "metrics": metrics,
                    "unlocked_achievements": newly_unlocked,
                    "points_earned": points_earned,
                    "points_before": points_before,
                    "total_points": total_points,
                    "level_before": level_before,
                    "level": current_level,
                    "level_up": level_up,
                    "points_to_next_level": _calculate_simulated_points_to_next_level(total_points),
                    "current_level_progress": _calculate_simulated_level_progress(total_points),
                    "feedback": feedback,
                }
            )

        final_metrics = _calculate_simulated_metrics(
            history,
            reference_date=parsed_default_reference_date,
        )

        processed_count = len(processed_keys)
        duplicated_count = len(records) - processed_count
        unlocked_codes_list = sorted(unlocked_codes)

        expectation_checks = {
            "processed_count_matches": (
                expected.get("processed_count") is None
                or expected.get("processed_count") == processed_count
            ),
            "duplicated_count_matches": (
                expected.get("duplicated_count") is None
                or expected.get("duplicated_count") == duplicated_count
            ),
            "total_minutes_matches": (
                expected.get("total_minutes") is None
                or expected.get("total_minutes") == final_metrics.get("total_minutes")
            ),
            "total_points_matches": (
                expected.get("total_points") is None
                or expected.get("total_points") == total_points
            ),
            "final_level_matches": (
                expected.get("final_level") is None
                or expected.get("final_level") == current_level
            ),
            "unlocked_codes_match": (
                expected.get("unlocked_codes") is None
                or sorted(expected.get("unlocked_codes")) == unlocked_codes_list
            ),
        }

        batch_results.append(
            {
                "batch_name": batch_name,
                "records_received": len(records),
                "processed_count": processed_count,
                "duplicated_count": duplicated_count,
                "final_metrics": final_metrics,
                "total_points": total_points,
                "level": current_level,
                "points_to_next_level": _calculate_simulated_points_to_next_level(total_points),
                "current_level_progress": _calculate_simulated_level_progress(total_points),
                "unlocked_codes": unlocked_codes_list,
                "record_results": record_results,
                "processed_event_keys": sorted(processed_event_keys),
                "expected": expected,
                "expectation_checks": expectation_checks,
                "all_expectations_match": all(expectation_checks.values()),
            }
        )

    return batch_results