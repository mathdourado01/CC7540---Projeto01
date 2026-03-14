from collections import defaultdict
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


def calculate_dashboard_metrics(history: list[dict]) -> dict:
    total_sessions = len(history)
    total_minutes = sum(item["studied_minutes"] for item in history)
    total_hours = round(total_minutes / 60, 2)

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
        "subject_chart": subject_chart,
        "daily_chart": daily_chart,
    }