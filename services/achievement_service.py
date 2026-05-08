from services.supabase_client import get_supabase_client

from rules.achievement_rules import (
    ACHIEVEMENT_CRITERIA,
    filter_new_reached_achievements,
    build_achievement_processing_response,
    group_achievement_goals_by_criteria,
)


def get_active_achievements(access_token: str, refresh_token: str) -> list[dict]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("achievements")
        .select(
            "id, code, title, description, criteria_type, criteria_value, points_reward, icon"
        )
        .eq("is_active", True)
        .execute()
    )

    return response.data or []


def get_user_unlocked_achievement_ids(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> set[str]:
    supabase = get_supabase_client(access_token, refresh_token)

    response = (
        supabase.table("user_achievements")
        .select("achievement_id")
        .eq("user_id", user_id)
        .execute()
    )

    return {
        item.get("achievement_id")
        for item in (response.data or [])
        if item.get("achievement_id") is not None
    }


def save_unlocked_achievements(
    user_id: str,
    achievements: list[dict],
    access_token: str,
    refresh_token: str,
) -> list[dict]:
    if not achievements:
        return []

    supabase = get_supabase_client(access_token, refresh_token)

    payload = [
        {
            "user_id": user_id,
            "achievement_id": achievement.get("id"),
        }
        for achievement in achievements
        if achievement.get("id") is not None
    ]

    if not payload:
        return []

    response = (
        supabase.table("user_achievements")
        .upsert(payload, on_conflict="user_id,achievement_id")
        .execute()
    )

    saved_ids = {
        item.get("achievement_id")
        for item in (response.data or [])
        if item.get("achievement_id") is not None
    }

    return [
        achievement
        for achievement in achievements
        if achievement.get("id") in saved_ids
    ]


def check_reached_achievements(
    user_id: str,
    metrics: dict,
    streak_data: dict,
    access_token: str,
    refresh_token: str,
) -> dict:
    achievements = get_active_achievements(access_token, refresh_token)

    already_unlocked_ids = get_user_unlocked_achievement_ids(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    reached_achievements = filter_new_reached_achievements(
        achievements=achievements,
        already_unlocked_ids=already_unlocked_ids,
        metrics=metrics,
        streak_data=streak_data,
    )

    saved_achievements = save_unlocked_achievements(
        user_id=user_id,
        achievements=reached_achievements,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    already_unlocked_count = len(achievements) - len(reached_achievements)

    return build_achievement_processing_response(
        unlocked_achievements=saved_achievements,
        already_unlocked_count=already_unlocked_count,
    )


def get_available_achievement_goals(
    access_token: str,
    refresh_token: str,
) -> dict:
    achievements = get_active_achievements(access_token, refresh_token)
    goals_by_criteria = group_achievement_goals_by_criteria(achievements)

    return {
        "success": True,
        "criteria": ACHIEVEMENT_CRITERIA,
        "goals_by_criteria": goals_by_criteria,
        "total_goals": sum(
            len(group["achievements"])
            for group in goals_by_criteria.values()
        ),
    }