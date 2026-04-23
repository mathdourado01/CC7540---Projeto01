from collections import defaultdict
from datetime import date

import pandas as pd
import streamlit as st

from services.supabase_client import get_supabase_client


@st.cache_data(ttl=60, show_spinner=False)
def get_study_history(user_id: str, access_token: str, refresh_token: str) -> list[dict]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("study_sessions")
        .select("id, subject_name, studied_minutes, studied_at, created_at")
        .eq("user_id", user_id)
        .order("studied_at", desc=True)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


def _parse_study_date(value: str | date | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def _get_unique_study_dates(history: list[dict]) -> list[date]:
    unique_dates = {
        parsed_date
        for item in history
        if (parsed_date := _parse_study_date(item.get("studied_at"))) is not None
    }

    return sorted(unique_dates, reverse=True)


def calculate_streak_state_from_dates(
    study_dates: list[str | date],
    reference_date: date | None = None,
) -> dict:
    if reference_date is None:
        reference_date = date.today()

    unique_dates = sorted(
        {
            parsed_date
            for raw_date in study_dates
            if (parsed_date := _parse_study_date(raw_date)) is not None
        },
        reverse=True,
    )

    if not unique_dates:
        return {
            "current_streak": 0,
            "latest_study_date": None,
            "streak_broken": False,
        }

    latest_study_date = unique_dates[0]
    days_without_study = (reference_date - latest_study_date).days

    if days_without_study > 1:
        return {
            "current_streak": 0,
            "latest_study_date": latest_study_date,
            "streak_broken": True,
        }

    streak_days = 1
    previous_date = latest_study_date

    for next_date in unique_dates[1:]:
        difference_in_days = (previous_date - next_date).days

        if difference_in_days == 1:
            streak_days += 1
            previous_date = next_date
            continue

        break

    return {
        "current_streak": streak_days,
        "latest_study_date": latest_study_date,
        "streak_broken": False,
    }


def calculate_highest_streak_from_dates(study_dates: list[str | date]) -> int:
    unique_dates = sorted(
        {
            parsed_date
            for raw_date in study_dates
            if (parsed_date := _parse_study_date(raw_date)) is not None
        }
    )

    if not unique_dates:
        return 0

    highest_streak = 1
    current_sequence = 1

    for index in range(1, len(unique_dates)):
        difference_in_days = (unique_dates[index] - unique_dates[index - 1]).days

        if difference_in_days == 1:
            current_sequence += 1
        else:
            current_sequence = 1

        if current_sequence > highest_streak:
            highest_streak = current_sequence

    return highest_streak


def _calculate_current_streak(history: list[dict]) -> int:
    unique_study_dates = _get_unique_study_dates(history)
    streak_state = calculate_streak_state_from_dates(unique_study_dates)

    return streak_state["current_streak"]


def _calculate_highest_streak(history: list[dict]) -> int:
    unique_study_dates = _get_unique_study_dates(history)
    return calculate_highest_streak_from_dates(unique_study_dates)


def calculate_dashboard_metrics(history: list[dict]) -> dict:
    total_sessions = len(history)
    total_minutes = sum(item["studied_minutes"] for item in history)
    total_hours = round(total_minutes / 60, 2)
    current_streak = _calculate_current_streak(history)
    highest_streak = _calculate_highest_streak(history)

    minutes_per_subject = defaultdict(int)
    minutes_per_day = defaultdict(int)

    for item in history:
        minutes_per_subject[item["subject_name"]] += item["studied_minutes"]
        minutes_per_day[item["studied_at"]] += item["studied_minutes"]

    subject_chart = pd.DataFrame(
        [
            {
                "Disciplina": subject,
                "Horas": round(minutes / 60, 2)
            }
            for subject, minutes in minutes_per_subject.items()
        ]
    )

    daily_chart = pd.DataFrame(
        [
            {
                "Data": day,
                "Horas": round(minutes / 60, 2)
            }
            for day, minutes in minutes_per_day.items()
        ]
    )

    if not subject_chart.empty:
        subject_chart = subject_chart.sort_values(by="Horas", ascending=False)

    if not daily_chart.empty:
        daily_chart = daily_chart.sort_values(by="Data", ascending=True)

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
        "current_streak": current_streak,
        "highest_streak": highest_streak,
        "subject_chart": subject_chart,
        "daily_chart": daily_chart,
    }