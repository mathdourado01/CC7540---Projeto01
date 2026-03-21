import math
import streamlit as st

from services.supabase_client import get_supabase_client


@st.cache_data(ttl=30, show_spinner=False)
def get_group_ranking(access_token: str, refresh_token: str, period_days: int) -> list[dict]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = supabase.rpc(
        "get_group_ranking",
        {"p_period_days": period_days}
    ).execute()

    return response.data or []


def sort_ranking(rows: list[dict], mode: str) -> list[dict]:
    if mode == "minutes":
        return sorted(
            rows,
            key=lambda row: (
                row["rank_by_minutes"],
                -row["total_minutes"],
                -row["total_points"],
                str(row["user_id"]),
            ),
        )

    return sorted(
        rows,
        key=lambda row: (
            row["rank_by_points"],
            -row["total_points"],
            -row["total_minutes"],
            str(row["user_id"]),
        ),
    )


def get_user_position(rows: list[dict], user_id: str, mode: str) -> int | None:
    for row in rows:
        if row["user_id"] == user_id:
            return row["rank_by_minutes"] if mode == "minutes" else row["rank_by_points"]
    return None


def paginate_rows(rows: list[dict], page: int, page_size: int = 10) -> tuple[list[dict], int]:
    total_pages = max(1, math.ceil(len(rows) / page_size))
    current_page = max(1, min(page, total_pages))

    start = (current_page - 1) * page_size
    end = start + page_size

    return rows[start:end], total_pages
