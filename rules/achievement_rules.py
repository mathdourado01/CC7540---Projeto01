ACHIEVEMENT_CRITERIA = {
    "total_sessions": {
        "label": "Total de sessões",
        "description": "Conquista baseada na quantidade total de sessões registradas.",
        "metric_source": "metrics",
    },
    "total_minutes": {
        "label": "Tempo total estudado",
        "description": "Conquista baseada no total de minutos estudados.",
        "metric_source": "metrics",
    },
    "current_streak": {
        "label": "Streak atual",
        "description": "Conquista baseada na sequência atual de dias estudados.",
        "metric_source": "streak",
    },
    "longest_streak": {
        "label": "Maior streak",
        "description": "Conquista baseada na maior sequência de estudos já alcançada.",
        "metric_source": "streak",
    },
}


DEFAULT_ACHIEVEMENTS = [
    {
        "code": "first_session",
        "title": "Primeiro Passo",
        "description": "Você registrou sua primeira sessão de estudo.",
        "criteria_type": "total_sessions",
        "criteria_value": 1,
        "points_reward": 10,
        "icon": "🐭",
    },
    {
        "code": "three_sessions",
        "title": "Entrando no Ritmo",
        "description": "Você registrou 3 sessões de estudo.",
        "criteria_type": "total_sessions",
        "criteria_value": 3,
        "points_reward": 20,
        "icon": "📚",
    },
    {
        "code": "ten_sessions",
        "title": "Rato de Biblioteca",
        "description": "Você registrou 10 sessões de estudo.",
        "criteria_type": "total_sessions",
        "criteria_value": 10,
        "points_reward": 50,
        "icon": "🐀",
    },
    {
        "code": "one_hour_total",
        "title": "Primeira Hora",
        "description": "Você acumulou 60 minutos de estudo.",
        "criteria_type": "total_minutes",
        "criteria_value": 60,
        "points_reward": 20,
        "icon": "⏱️",
    },
    {
        "code": "five_hours_total",
        "title": "Foco de Verdade",
        "description": "Você acumulou 5 horas de estudo.",
        "criteria_type": "total_minutes",
        "criteria_value": 300,
        "points_reward": 50,
        "icon": "🔥",
    },
    {
        "code": "streak_3_days",
        "title": "Trinca de Foco",
        "description": "Você estudou por 3 dias seguidos.",
        "criteria_type": "current_streak",
        "criteria_value": 3,
        "points_reward": 30,
        "icon": "🔥",
    },
    {
        "code": "streak_7_days",
        "title": "Semana Imparável",
        "description": "Você estudou por 7 dias seguidos.",
        "criteria_type": "current_streak",
        "criteria_value": 7,
        "points_reward": 70,
        "icon": "🏆",
    },
]


def is_supported_achievement_criteria(criteria_type: str) -> bool:
    return criteria_type in ACHIEVEMENT_CRITERIA


def get_metric_value(
    criteria_type: str,
    metrics: dict,
    streak_data: dict,
) -> int:
    if not is_supported_achievement_criteria(criteria_type):
        return 0

    metric_source = ACHIEVEMENT_CRITERIA[criteria_type]["metric_source"]

    if metric_source == "metrics":
        return int(metrics.get(criteria_type, 0) or 0)

    if metric_source == "streak":
        return int(
            streak_data.get(
                criteria_type,
                streak_data.get("highest_streak", 0)
                if criteria_type == "longest_streak"
                else 0,
            )
            or 0
        )

    return 0


def was_achievement_reached(
    achievement: dict,
    metrics: dict,
    streak_data: dict,
) -> bool:
    criteria_type = achievement.get("criteria_type")
    criteria_value = int(achievement.get("criteria_value", 0) or 0)

    current_value = get_metric_value(
        criteria_type=criteria_type,
        metrics=metrics,
        streak_data=streak_data,
    )

    return current_value >= criteria_value


def filter_new_reached_achievements(
    achievements: list[dict],
    already_unlocked_ids: set[str],
    metrics: dict,
    streak_data: dict,
) -> list[dict]:
    reached_achievements = []

    for achievement in achievements:
        achievement_id = achievement.get("id")

        if achievement_id in already_unlocked_ids:
            continue

        if was_achievement_reached(
            achievement=achievement,
            metrics=metrics,
            streak_data=streak_data,
        ):
            reached_achievements.append(
                {
                    "id": achievement.get("id"),
                    "code": achievement.get("code"),
                    "title": achievement.get("title"),
                    "description": achievement.get("description"),
                    "criteria_type": achievement.get("criteria_type"),
                    "criteria_value": achievement.get("criteria_value"),
                    "points_reward": achievement.get("points_reward", 0),
                    "icon": achievement.get("icon"),
                }
            )

    return reached_achievements


def build_achievement_processing_response(
    unlocked_achievements: list[dict],
    already_unlocked_count: int = 0,
) -> dict:
    formatted_achievements = []

    for achievement in unlocked_achievements:
        formatted_achievements.append(
            {
                "id": achievement.get("id"),
                "code": achievement.get("code"),
                "title": achievement.get("title"),
                "description": achievement.get("description"),
                "points_reward": achievement.get("points_reward", 0),
                "icon": achievement.get("icon"),
            }
        )

    return {
        "success": True,
        "unlocked_achievements": formatted_achievements,
        "total_unlocked": len(formatted_achievements),
        "already_unlocked_count": already_unlocked_count,
        "has_new_achievements": len(formatted_achievements) > 0,
        "message": (
            "Novas conquistas desbloqueadas."
            if formatted_achievements
            else "Nenhuma nova conquista desbloqueada."
        ),
    }


def group_achievement_goals_by_criteria(achievements: list[dict]) -> dict:
    goals_by_criteria = {}

    for achievement in achievements:
        criteria_type = achievement.get("criteria_type")

        if not is_supported_achievement_criteria(criteria_type):
            continue

        if criteria_type not in goals_by_criteria:
            goals_by_criteria[criteria_type] = {
                "criteria": ACHIEVEMENT_CRITERIA[criteria_type],
                "achievements": [],
            }

        goals_by_criteria[criteria_type]["achievements"].append(
            {
                "id": achievement.get("id"),
                "code": achievement.get("code"),
                "title": achievement.get("title"),
                "description": achievement.get("description"),
                "criteria_value": achievement.get("criteria_value"),
                "points_reward": achievement.get("points_reward", 0),
                "icon": achievement.get("icon"),
            }
        )

    return goals_by_criteria