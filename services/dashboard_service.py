from collections import defaultdict
import pandas as pd

from services.supabase_client import get_supabase_client


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

    for item in history:
        minutes_per_subject[item["subject_name"]] += item["studied_minutes"]

    subject_table = pd.DataFrame(
        [
            {
                "Disciplina": subject,
                "Horas": round(minutes / 60, 2)
            }
            for subject, minutes in minutes_per_subject.items()
        ]
    )

    if not subject_table.empty:
        subject_table = subject_table.sort_values(by="Horas", ascending=False)

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
        "subject_table": subject_table,
    }
