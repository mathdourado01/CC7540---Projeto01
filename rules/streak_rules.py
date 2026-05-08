from datetime import date


def parse_study_date(value: str | date | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def calculate_current_streak_from_dates(
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


def calculate_longest_streak_from_dates(study_dates: list[str | date]) -> int:
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

    current_streak_state = calculate_current_streak_from_dates(
        study_dates,
        reference_date=reference_date,
    )

    longest_streak = calculate_longest_streak_from_dates(study_dates)

    return {
        "current_streak": current_streak_state["current_streak"],
        "longest_streak": longest_streak,
        "highest_streak": longest_streak,
        "last_study_date": current_streak_state["last_study_date"],
        "latest_study_date": current_streak_state["last_study_date"],
        "streak_broken": current_streak_state["streak_broken"],
    }


def get_streak_status_message(status: str) -> str:
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


def build_streak_processing_response(
    streak_data: dict,
    status: str,
    success: bool = True,
    message: str | None = None,
) -> dict:
    status_labels = {
        "started": "iniciada",
        "maintained": "mantida",
        "incremented": "incrementada",
        "reset": "resetada",
        "recalculated": "recalculada",
        "invalid_date": "data inválida",
        "none": "sem streak",
    }

    longest_streak = int(
        streak_data.get(
            "longest_streak",
            streak_data.get("highest_streak", 0),
        )
        or 0
    )

    return {
        "success": success,
        "status": status,
        "status_label": status_labels.get(status, "atualizada"),
        "message": message or get_streak_status_message(status),
        "current_streak": int(streak_data.get("current_streak", 0) or 0),
        "longest_streak": longest_streak,
        "highest_streak": longest_streak,
        "last_study_date": streak_data.get("last_study_date"),
        "latest_study_date": streak_data.get(
            "latest_study_date",
            streak_data.get("last_study_date"),
        ),
        "user_id": streak_data.get("user_id"),
    }


def calculate_streak_update_after_session(
    previous_streak: dict,
    studied_at: date | str,
) -> dict:
    study_date = parse_study_date(studied_at)
    previous_last_study_date = parse_study_date(previous_streak.get("last_study_date"))

    previous_current_streak = int(previous_streak.get("current_streak", 0) or 0)
    previous_longest_streak = int(
        previous_streak.get(
            "longest_streak",
            previous_streak.get("highest_streak", 0),
        )
        or 0
    )

    if study_date is None:
        return build_streak_processing_response(
            streak_data={
                "user_id": previous_streak.get("user_id"),
                "current_streak": previous_current_streak,
                "longest_streak": previous_longest_streak,
                "highest_streak": previous_longest_streak,
                "last_study_date": (
                    previous_last_study_date.isoformat()
                    if previous_last_study_date is not None
                    else None
                ),
            },
            status="invalid_date",
            success=False,
            message="Data de estudo inválida.",
        )

    if previous_last_study_date is None:
        new_current_streak = 1
        streak_status = "started"

    else:
        days_difference = (study_date - previous_last_study_date).days

        if days_difference == 0:
            new_current_streak = previous_current_streak
            streak_status = "maintained"

        elif days_difference == 1:
            new_current_streak = previous_current_streak + 1
            streak_status = "incremented"

        elif days_difference > 1:
            new_current_streak = 1
            streak_status = "reset"

        else:
            return {
                "success": True,
                "status": "needs_recalculation",
                "status_label": "precisa recalcular",
                "message": "Sessão anterior ao último estudo. Recalcule pelo histórico completo.",
                "current_streak": previous_current_streak,
                "longest_streak": previous_longest_streak,
                "highest_streak": previous_longest_streak,
                "last_study_date": (
                    previous_last_study_date.isoformat()
                    if previous_last_study_date is not None
                    else None
                ),
                "latest_study_date": (
                    previous_last_study_date.isoformat()
                    if previous_last_study_date is not None
                    else None
                ),
                "user_id": previous_streak.get("user_id"),
            }

    new_longest_streak = max(previous_longest_streak, new_current_streak)

    return build_streak_processing_response(
        streak_data={
            "user_id": previous_streak.get("user_id"),
            "current_streak": new_current_streak,
            "longest_streak": new_longest_streak,
            "highest_streak": new_longest_streak,
            "last_study_date": study_date.isoformat(),
            "latest_study_date": study_date.isoformat(),
        },
        status=streak_status,
        success=True,
    )