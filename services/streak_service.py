from datetime import date

from services.supabase_client import get_supabase_client

from rules.streak_rules import (
    parse_study_date,
    calculate_streak_summary_from_history,
    build_streak_processing_response,
    calculate_streak_update_after_session,
)

def parse_study_date(value: str | date | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def _calculate_current_streak_from_dates(
    study_dates: list[str | date],
    reference_date: date | None = None,
) -> dict:
    if reference_date is None:
        reference_date = date.today()

    unique_dates = sorted(
        {
            parsed_date
            for raw_date in study_dates
            if (parsed_date := parse_study_date(raw_date)) is not None
        },
        reverse=True,
    )

    if not unique_dates:
        return {
            "current_streak": 0,
            "last_study_date": None,
            "streak_broken": False,
        }

    last_study_date = unique_dates[0]
    days_without_study = (reference_date - last_study_date).days

    if days_without_study > 1:
        return {
            "current_streak": 0,
            "last_study_date": last_study_date,
            "streak_broken": True,
        }

    current_streak = 1
    previous_date = last_study_date

    for next_date in unique_dates[1:]:
        difference_in_days = (previous_date - next_date).days

        if difference_in_days == 1:
            current_streak += 1
            previous_date = next_date
        else:
            break

    return {
        "current_streak": current_streak,
        "last_study_date": last_study_date,
        "streak_broken": False,
    }


def _calculate_longest_streak_from_dates(study_dates: list[str | date]) -> int:
    unique_dates = sorted(
        {
            parsed_date
            for raw_date in study_dates
            if (parsed_date := parse_study_date(raw_date)) is not None
        }
    )

    if not unique_dates:
        return 0

    longest_streak = 1
    current_sequence = 1

    for index in range(1, len(unique_dates)):
        difference_in_days = (unique_dates[index] - unique_dates[index - 1]).days

        if difference_in_days == 1:
            current_sequence += 1
        else:
            current_sequence = 1

        if current_sequence > longest_streak:
            longest_streak = current_sequence

    return longest_streak


def calculate_streak_summary_from_history(
    history: list[dict],
    reference_date: date | None = None,
) -> dict:
    study_dates = [item.get("studied_at") for item in history]

    current_streak_state = _calculate_current_streak_from_dates(
        study_dates,
        reference_date=reference_date,
    )

    longest_streak = _calculate_longest_streak_from_dates(study_dates)

    return {
        "current_streak": current_streak_state["current_streak"],
        "longest_streak": longest_streak,
        "highest_streak": longest_streak,
        "last_study_date": current_streak_state["last_study_date"],
        "latest_study_date": current_streak_state["last_study_date"],
        "streak_broken": current_streak_state["streak_broken"],
    }


def get_user_streak(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("user_streaks")
        .select("user_id, current_streak, longest_streak, last_study_date, created_at, updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if response.data:
        streak = response.data[0]

        return {
            "user_id": streak["user_id"],
            "current_streak": streak.get("current_streak", 0),
            "longest_streak": streak.get("longest_streak", 0),
            "highest_streak": streak.get("longest_streak", 0),
            "last_study_date": streak.get("last_study_date"),
            "latest_study_date": streak.get("last_study_date"),
            "created_at": streak.get("created_at"),
            "updated_at": streak.get("updated_at"),
        }

    return create_initial_user_streak(user_id, access_token, refresh_token)


def create_initial_user_streak(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    supabase = get_supabase_client(access_token, refresh_token)

    payload = {
        "user_id": user_id,
        "current_streak": 0,
        "longest_streak": 0,
        "last_study_date": None,
    }

    response = (
        supabase.table("user_streaks")
        .insert(payload)
        .execute()
    )

    streak = response.data[0] if response.data else payload

    return {
        "user_id": streak["user_id"],
        "current_streak": streak.get("current_streak", 0),
        "longest_streak": streak.get("longest_streak", 0),
        "highest_streak": streak.get("longest_streak", 0),
        "last_study_date": streak.get("last_study_date"),
        "latest_study_date": streak.get("last_study_date"),
    }


def update_user_streak(
    user_id: str,
    access_token: str,
    refresh_token: str,
    current_streak: int,
    longest_streak: int,
    last_study_date: date | str | None,
) -> dict:
    supabase = get_supabase_client(access_token, refresh_token)

    parsed_last_study_date = parse_study_date(last_study_date)

    payload = {
        "user_id": user_id,
        "current_streak": int(current_streak),
        "longest_streak": int(longest_streak),
        "last_study_date": (
            parsed_last_study_date.isoformat()
            if parsed_last_study_date is not None
            else None
        ),
    }

    response = (
        supabase.table("user_streaks")
        .upsert(payload, on_conflict="user_id")
        .execute()
    )

    streak = response.data[0] if response.data else payload

    return {
        "user_id": streak["user_id"],
        "current_streak": streak.get("current_streak", 0),
        "longest_streak": streak.get("longest_streak", 0),
        "highest_streak": streak.get("longest_streak", 0),
        "last_study_date": streak.get("last_study_date"),
        "latest_study_date": streak.get("last_study_date"),
    }


def recalculate_and_save_user_streak(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("study_sessions")
        .select("studied_at")
        .eq("user_id", user_id)
        .order("studied_at", desc=True)
        .execute()
    )

    history = response.data or []
    streak_summary = calculate_streak_summary_from_history(history)

    return update_user_streak(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        current_streak=streak_summary["current_streak"],
        longest_streak=streak_summary["longest_streak"],
        last_study_date=streak_summary["last_study_date"],
    )

def update_streak_after_study_session(
    user_id: str,
    studied_at: date | str,
    access_token: str,
    refresh_token: str,
) -> dict:
    previous_streak = get_user_streak(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    previous_streak["user_id"] = user_id

    streak_update = calculate_streak_update_after_session(
        previous_streak=previous_streak,
        studied_at=studied_at,
    )

    if not streak_update.get("success"):
        return streak_update

    if streak_update.get("status") == "needs_recalculation":
        recalculated_streak = recalculate_and_save_user_streak(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        return build_streak_processing_response(
            streak_data=recalculated_streak,
            status="recalculated",
            success=True,
            message="Streak recalculada com base no histórico.",
        )

    updated_streak = update_user_streak(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        current_streak=streak_update.get("current_streak", 0),
        longest_streak=streak_update.get("longest_streak", 0),
        last_study_date=streak_update.get("last_study_date"),
    )

    return build_streak_processing_response(
        streak_data=updated_streak,
        status=streak_update.get("status", "none"),
        success=True,
        message=streak_update.get("message"),
    )

def build_streak_processing_response(
    streak_data: dict,
    status: str,
    success: bool = True,
    message: str | None = None,
) -> dict:
    """
    Monta um retorno padronizado para qualquer processamento de streak.
    """

    status_labels = {
        "started": "iniciada",
        "maintained": "mantida",
        "incremented": "incrementada",
        "reset": "resetada",
        "recalculated": "recalculada",
        "invalid_date": "data inválida",
        "none": "sem streak",
    }

    longest_streak = streak_data.get(
        "longest_streak",
        streak_data.get("highest_streak", 0),
    )

    return {
        "success": success,
        "status": status,
        "status_label": status_labels.get(status, "atualizada"),
        "message": message or get_streak_status_message(status),
        "current_streak": streak_data.get("current_streak", 0),
        "longest_streak": longest_streak,
        "highest_streak": longest_streak,
        "last_study_date": streak_data.get("last_study_date"),
        "user_id": streak_data.get("user_id"),
    }
def get_streak_status_message(status: str) -> str:
    """
    Retorna uma mensagem amigável com base no status da streak.
    """

    messages = {
        "started": "Streak iniciada com sucesso.",
        "maintained": "Streak mantida. Você já registrou estudo nesta data.",
        "incremented": "Streak incrementada. Mais um dia seguido de estudo!",
        "reset": "Streak reiniciada após quebra na sequência.",
        "recalculated": "Streak recalculada com base no histórico.",
        "invalid_date": "Data de estudo inválida.",
        "none": "Nenhuma streak ativa no momento.",
    }

    return messages.get(status, "Status da streak atualizado.")

def recalculate_streak_on_app_open(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Recalcula e persiste a streak do usuário ao abrir o sistema.

    Essa rotina garante que a tela inicial mostre uma streak coerente
    mesmo quando o usuário ficou dias sem estudar.
    """

    recalculated_streak = recalculate_and_save_user_streak(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    return build_streak_processing_response(
        streak_data=recalculated_streak,
        status="recalculated",
        success=True,
        message="Streak recalculada ao abrir o sistema.",
    )