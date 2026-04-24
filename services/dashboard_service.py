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


@st.cache_data(ttl=30, show_spinner=False)
def get_streak_summary(user_id: str, access_token: str, refresh_token: str) -> dict:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("study_sessions")
        .select("studied_at")
        .eq("user_id", user_id)
        .order("studied_at", desc=True)
        .execute()
    )

    history = response.data or []
    return recalculate_streaks_from_history(history)


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


def recalculate_streaks_from_history(
    history: list[dict],
    reference_date: date | None = None,
) -> dict:
    unique_study_dates = _get_unique_study_dates(history)

    streak_state = calculate_streak_state_from_dates(
        unique_study_dates,
        reference_date=reference_date,
    )

    highest_streak = calculate_highest_streak_from_dates(unique_study_dates)

    return {
        "current_streak": streak_state["current_streak"],
        "highest_streak": highest_streak,
        "latest_study_date": streak_state["latest_study_date"],
        "streak_broken": streak_state["streak_broken"],
        "total_unique_study_days": len(unique_study_dates),
        "recalculated_from_history": True,
    }


def simulate_streak_batches(
    test_batches: list[dict],
    default_reference_date: date | str | None = None,
) -> list[dict]:
    parsed_default_reference_date = _parse_study_date(default_reference_date)

    simulation_results = []

    for index, test_case in enumerate(test_batches, start=1):
        case_name = test_case.get("name") or f"Caso {index}"
        study_dates = test_case.get("study_dates", [])
        expected_current_streak = test_case.get("expected_current_streak")
        expected_highest_streak = test_case.get("expected_highest_streak")
        expected_streak_broken = test_case.get("expected_streak_broken")

        reference_date = _parse_study_date(test_case.get("reference_date"))
        if reference_date is None:
            reference_date = parsed_default_reference_date

        unique_dates = sorted(
            {
                parsed_date
                for raw_date in study_dates
                if (parsed_date := _parse_study_date(raw_date)) is not None
            },
            reverse=True,
        )

        streak_state = calculate_streak_state_from_dates(
            unique_dates,
            reference_date=reference_date,
        )
        highest_streak = calculate_highest_streak_from_dates(unique_dates)

        current_streak_matches = (
            expected_current_streak is None
            or streak_state["current_streak"] == expected_current_streak
        )
        highest_streak_matches = (
            expected_highest_streak is None
            or highest_streak == expected_highest_streak
        )
        streak_broken_matches = (
            expected_streak_broken is None
            or streak_state["streak_broken"] == expected_streak_broken
        )

        simulation_results.append(
            {
                "case_name": case_name,
                "reference_date": reference_date,
                "input_study_dates": study_dates,
                "unique_study_dates": unique_dates,
                "current_streak": streak_state["current_streak"],
                "highest_streak": highest_streak,
                "latest_study_date": streak_state["latest_study_date"],
                "streak_broken": streak_state["streak_broken"],
                "total_unique_study_days": len(unique_dates),
                "expected_current_streak": expected_current_streak,
                "expected_highest_streak": expected_highest_streak,
                "expected_streak_broken": expected_streak_broken,
                "current_streak_matches": current_streak_matches,
                "highest_streak_matches": highest_streak_matches,
                "streak_broken_matches": streak_broken_matches,
                "all_expectations_match": (
                    current_streak_matches
                    and highest_streak_matches
                    and streak_broken_matches
                ),
            }
        )

    return simulation_results


def _calculate_current_streak(history: list[dict]) -> int:
    streak_summary = recalculate_streaks_from_history(history)
    return streak_summary["current_streak"]


def _calculate_highest_streak(history: list[dict]) -> int:
    streak_summary = recalculate_streaks_from_history(history)
    return streak_summary["highest_streak"]


def calculate_dashboard_metrics(history: list[dict]) -> dict:
    total_sessions = len(history)
    total_minutes = sum(item["studied_minutes"] for item in history)
    total_hours = round(total_minutes / 60, 2)

    streak_summary = recalculate_streaks_from_history(history)
    current_streak = streak_summary["current_streak"]
    highest_streak = streak_summary["highest_streak"]

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
        "streak_broken": streak_summary["streak_broken"],
        "latest_study_date": streak_summary["latest_study_date"],
        "total_unique_study_days": streak_summary["total_unique_study_days"],
        "subject_chart": subject_chart,
        "daily_chart": daily_chart,
    }