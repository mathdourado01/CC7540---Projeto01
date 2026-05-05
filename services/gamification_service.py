from copy import deepcopy
from datetime import date
from time import perf_counter
from uuid import uuid4

from services.achievement_service import (
    DEFAULT_ACHIEVEMENTS,
    check_reached_achievements,
)
from services.dashboard_service import calculate_dashboard_metrics, get_study_history
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
    started_at: float | None = None,
) -> dict:
    """
    Monta um retorno único e rápido para o app.

    A ideia é que o app não precise entender todos os passos internos da
    gamificação. Ele recebe um pacote pronto com sessão, streak, conquistas,
    métricas, pontos liberados e mensagem visual imediata.
    """

    achievement_result = achievement_result or _build_empty_achievement_result()
    points_earned = _calculate_points_from_achievements(achievement_result)
    session_result = session_result or {}

    processing_seconds = None
    if started_at is not None:
        processing_seconds = round(perf_counter() - started_at, 4)

    has_new_achievements = achievement_result.get("has_new_achievements", False)
    should_show_visual_alert = bool(success and has_new_achievements)

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
        "points_earned": points_earned,
        "has_new_achievements": has_new_achievements,
        "should_show_visual_alert": should_show_visual_alert,
        "feedback": feedback or {
            "type": "success" if success else "error",
            "message": message,
        },
    }


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
    3. atualiza streak;
    4. recalcula métricas necessárias para conquistas;
    5. libera conquistas novas;
    6. devolve uma estrutura pronta para feedback imediato no Streamlit.
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
                "message": session_result.get("message", "Não foi possível registrar a sessão."),
            },
            started_at=started_at,
        )

    if session_result.get("gamification_already_processed"):
        _clear_cached_study_history()
        updated_history = get_study_history(
            user_id,
            access_token,
            refresh_token,
        )
        updated_metrics = calculate_dashboard_metrics(updated_history)
        current_streak = calculate_streak_summary_from_history(updated_history)
        normalized_streak = _normalize_streak(current_streak)

        updated_metrics["current_streak"] = normalized_streak.get("current_streak", 0)
        updated_metrics["highest_streak"] = normalized_streak.get("highest_streak", 0)
        updated_metrics["longest_streak"] = normalized_streak.get("longest_streak", 0)
        updated_metrics["last_study_date"] = normalized_streak.get("last_study_date")

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

    normalized_streak = _normalize_streak(updated_streak)

    _clear_cached_study_history()
    updated_history = get_study_history(
        user_id,
        access_token,
        refresh_token,
    )
    updated_metrics = calculate_dashboard_metrics(updated_history)

    updated_metrics["current_streak"] = normalized_streak.get("current_streak", 0)
    updated_metrics["highest_streak"] = normalized_streak.get("highest_streak", 0)
    updated_metrics["longest_streak"] = normalized_streak.get("longest_streak", 0)
    updated_metrics["last_study_date"] = normalized_streak.get("last_study_date")

    achievement_result = check_reached_achievements(
        user_id=user_id,
        metrics=updated_metrics,
        streak_data=normalized_streak,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    mark_result = mark_study_session_gamification_processed(
        session_id=(session_result.get("session") or {}).get("id"),
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not mark_result.get("success"):
        return build_fast_gamification_response(
            success=False,
            message=mark_result.get(
                "message",
                "A sessão foi registrada, mas não foi possível finalizar a gamificação.",
            ),
            processing_key=processing_key,
            session_result=session_result,
            streak_result=normalized_streak,
            achievement_result=achievement_result,
            metrics=updated_metrics,
            dashboard_history=updated_history,
            feedback={
                "type": "warning",
                "message": mark_result.get(
                    "message",
                    "A sessão foi registrada, mas não foi possível finalizar a gamificação.",
                ),
            },
            started_at=started_at,
        )

    feedback = _build_streak_feedback(previous_streak, normalized_streak)

    if achievement_result.get("has_new_achievements"):
        total_unlocked = achievement_result.get("total_unlocked", 0)
        points_earned = _calculate_points_from_achievements(achievement_result)
        feedback = {
            "type": "success",
            "message": (
                f"🏆 {total_unlocked} nova(s) conquista(s) desbloqueada(s)! "
                f"+{points_earned} pontos."
            ),
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
      para exibição imediata no app.
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
        unlocked_codes = set()
        total_points = 0
        record_results = []

        for record_index, record in enumerate(records, start=1):
            processing_key = record.get("processing_key") or f"{batch_name}_{record_index}"
            studied_at = _parse_study_date(record.get("studied_at"))
            reference_date = _parse_study_date(record.get("reference_date"))
            if reference_date is None:
                reference_date = parsed_default_reference_date

            if processing_key in processed_keys:
                metrics = _calculate_simulated_metrics(history, reference_date=reference_date)
                record_results.append(
                    {
                        "record_index": record_index,
                        "processing_key": processing_key,
                        "status": "duplicated",
                        "processed": False,
                        "message": "Registro ignorado porque a chave de processamento já foi usada.",
                        "metrics": metrics,
                        "unlocked_achievements": [],
                        "points_earned": 0,
                        "total_points": total_points,
                        "feedback": {
                            "type": "info",
                            "message": "Registro duplicado ignorado. Nenhum ponto foi duplicado.",
                        },
                    }
                )
                continue

            processed_keys.add(processing_key)

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
            total_points += points_earned

            has_new_achievements = len(newly_unlocked) > 0

            record_results.append(
                {
                    "record_index": record_index,
                    "processing_key": processing_key,
                    "status": "processed",
                    "processed": True,
                    "message": "Registro processado pela gamificação.",
                    "metrics": metrics,
                    "unlocked_achievements": newly_unlocked,
                    "points_earned": points_earned,
                    "total_points": total_points,
                    "feedback": {
                        "type": "success" if has_new_achievements else "info",
                        "message": (
                            f"{len(newly_unlocked)} conquista(s) desbloqueada(s). +{points_earned} pontos."
                            if has_new_achievements
                            else "Registro salvo sem novas conquistas."
                        ),
                    },
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
                "unlocked_codes": unlocked_codes_list,
                "record_results": record_results,
                "expected": expected,
                "expectation_checks": expectation_checks,
                "all_expectations_match": all(expectation_checks.values()),
            }
        )

    return batch_results