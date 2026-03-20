import math

from services.supabase_client import get_supabase_client


def get_basic_ranking(access_token: str, refresh_token: str) -> list[dict]:
    supabase = get_supabase_client(access_token, refresh_token)

    sessions_response = (
        supabase.table("study_sessions")
        .select("user_id, studied_minutes")
        .execute()
    )

    sessions = sessions_response.data or []
    if not sessions:
        return []

    aggregated: dict[str, dict] = {}
    for row in sessions:
        user_id = row["user_id"]
        if user_id not in aggregated:
            aggregated[user_id] = {
                "user_id": user_id,
                "total_points": 0,
                "total_minutes": 0,
            }

        aggregated[user_id]["total_points"] += 1
        aggregated[user_id]["total_minutes"] += int(row["studied_minutes"])

    user_ids = list(aggregated.keys())

    profiles_response = (
        supabase.table("profiles")
        .select("id, full_name, is_private")
        .in_("id", user_ids)
        .execute()
    )

    profiles_map = {
        row["id"]: {
            "display_name": "Rato Estudioso" if row.get("is_private") else (row.get("full_name") or "Usuário"),
            "is_private": row.get("is_private", False),
        }
        for row in (profiles_response.data or [])
    }

    ranking_rows = []
    for user_id, row in aggregated.items():
        profile = profiles_map.get(user_id, {"display_name": "Usuário", "is_private": False})
        ranking_rows.append(
            {
                "user_id": user_id,
                "display_name": profile["display_name"],
                "is_private": profile["is_private"],
                "total_points": row["total_points"],
                "total_minutes": row["total_minutes"],
            }
        )

    ranking_rows = sorted(
        ranking_rows,
        key=lambda row: (-row["total_points"], -row["total_minutes"], str(row["user_id"])),
    )

    for index, row in enumerate(ranking_rows, start=1):
        row["position"] = index

    return ranking_rows


def get_user_position(rows: list[dict], user_id: str) -> int | None:
    for row in rows:
        if row["user_id"] == user_id:
            return row["position"]
    return None


def paginate_rows(rows: list[dict], page: int, page_size: int = 10) -> tuple[list[dict], int]:
    total_pages = max(1, math.ceil(len(rows) / page_size))
    current_page = max(1, min(page, total_pages))

    start = (current_page - 1) * page_size
    end = start + page_size

    return rows[start:end], total_pages
