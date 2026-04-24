from services.supabase_client import get_supabase_client

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
    """
    Verifica se o tipo de critério da conquista é suportado pelo sistema.
    """

    return criteria_type in ACHIEVEMENT_CRITERIA

def get_active_achievements(access_token: str, refresh_token: str) -> list[dict]:
    """
    Busca no Supabase todas as conquistas ativas cadastradas na tabela achievements.
    """

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
    """
    Busca no Supabase as conquistas que o usuário já desbloqueou.

    Retorna um conjunto com os IDs das conquistas já registradas
    na tabela user_achievements.
    """

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
    """
    Salva no Supabase apenas as conquistas novas desbloqueadas pelo usuário.

    A tabela user_achievements possui constraint unique(user_id, achievement_id),
    então mesmo que a função seja chamada duas vezes, o banco impede duplicidade.
    """

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
        .upsert(
            payload,
            on_conflict="user_id,achievement_id",
        )
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

def get_metric_value(
    criteria_type: str,
    metrics: dict,
    streak_data: dict,
) -> int:
    """
    Retorna o valor atual do usuário de acordo com o tipo de critério da conquista.
    """

    if not is_supported_achievement_criteria(criteria_type):
        return 0

    metric_source = ACHIEVEMENT_CRITERIA[criteria_type]["metric_source"]

    if metric_source == "metrics":
        return int(metrics.get(criteria_type, 0))

    if metric_source == "streak":
        return int(
            streak_data.get(
                criteria_type,
                streak_data.get("highest_streak", 0)
                if criteria_type == "longest_streak"
                else 0,
            )
        )

    return 0

def was_achievement_reached(
    achievement: dict,
    metrics: dict,
    streak_data: dict,
) -> bool:
    """
    Verifica se uma conquista específica foi atingida pelo usuário.
    """

    criteria_type = achievement.get("criteria_type")
    criteria_value = int(achievement.get("criteria_value", 0))

    current_value = get_metric_value(
        criteria_type=criteria_type,
        metrics=metrics,
        streak_data=streak_data,
    )

    return current_value >= criteria_value


def check_reached_achievements(
    user_id: str,
    metrics: dict,
    streak_data: dict,
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Verifica todas as conquistas ativas, identifica quais foram atingidas,
    ignora as que o usuário já desbloqueou e salva apenas as novas.
    """

    achievements = get_active_achievements(access_token, refresh_token)
    already_unlocked_ids = get_user_unlocked_achievement_ids(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

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

def build_achievement_processing_response(
    unlocked_achievements: list[dict],
    already_unlocked_count: int = 0,
) -> dict:
    """
    Monta um retorno padronizado para o processamento de conquistas.

    unlocked_achievements:
        conquistas novas liberadas neste processamento.

    already_unlocked_count:
        quantidade de conquistas atingidas, mas que o usuário já possuía.
    """

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

def get_available_achievement_goals(
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Retorna uma visão organizada das conquistas ativas e dos critérios suportados.
    Pode ser usada futuramente para exibir uma tela de conquistas/metas.
    """

    achievements = get_active_achievements(access_token, refresh_token)

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

    return {
        "success": True,
        "criteria": ACHIEVEMENT_CRITERIA,
        "goals_by_criteria": goals_by_criteria,
        "total_goals": sum(
            len(group["achievements"])
            for group in goals_by_criteria.values()
        ),
    }