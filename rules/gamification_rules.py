POINTS_PER_LEVEL = 100

SESSION_COMPLETION_POINTS = 10
POINTS_PER_30_MINUTES = 5
MAX_DURATION_BONUS_POINTS = 50


def normalize_points(value: int) -> int:
    """
    Garante que valores de pontos sejam sempre inteiros e não negativos.
    """

    points = int(value or 0)

    if points < 0:
        return 0

    return points


def calculate_level(total_points: int) -> int:
    """
    Calcula o nível do usuário com base na pontuação acumulada.

    Regra:
    - 0 a 99 pontos     -> nível 1
    - 100 a 199 pontos  -> nível 2
    - 200 a 299 pontos  -> nível 3
    - e assim por diante.
    """

    total_points = normalize_points(total_points)

    return (total_points // POINTS_PER_LEVEL) + 1


def calculate_points_inside_current_level(total_points: int) -> int:
    """
    Calcula quantos pontos o usuário já acumulou dentro do nível atual.
    """

    total_points = normalize_points(total_points)

    return total_points % POINTS_PER_LEVEL


def calculate_points_to_next_level(total_points: int) -> int:
    """
    Calcula quantos pontos faltam para o próximo nível.
    """

    points_inside_level = calculate_points_inside_current_level(total_points)

    return POINTS_PER_LEVEL - points_inside_level


def calculate_current_level_progress(total_points: int) -> dict:
    """
    Retorna o progresso completo do usuário dentro do nível atual.
    """

    total_points = normalize_points(total_points)

    current_level = calculate_level(total_points)
    points_inside_level = calculate_points_inside_current_level(total_points)
    points_to_next_level = calculate_points_to_next_level(total_points)

    progress_percentage = round(
        (points_inside_level / POINTS_PER_LEVEL) * 100,
        2,
    )

    return {
        "current_level": current_level,
        "total_points": total_points,
        "points_inside_level": points_inside_level,
        "points_required_in_level": POINTS_PER_LEVEL,
        "points_to_next_level": points_to_next_level,
        "progress_percentage": progress_percentage,
    }


def calculate_level_progression(
    previous_total_points: int,
    points_delta: int,
) -> dict:
    """
    Calcula a progressão de nível após o usuário ganhar novos pontos.

    Recebe:
    - previous_total_points: pontuação acumulada antes do processamento
    - points_delta: pontos ganhos no processamento atual

    Retorna:
    - pontuação anterior
    - pontuação ganha
    - pontuação atualizada
    - nível anterior
    - nível atualizado
    - se houve subida de nível
    - quantos níveis foram ganhos
    - progresso atual dentro do nível
    """

    previous_total_points = normalize_points(previous_total_points)
    points_delta = normalize_points(points_delta)

    updated_total_points = previous_total_points + points_delta

    previous_level = calculate_level(previous_total_points)
    updated_level = calculate_level(updated_total_points)

    level_up = updated_level > previous_level
    levels_gained = updated_level - previous_level

    return {
        "success": True,
        "previous_total_points": previous_total_points,
        "points_delta": points_delta,
        "updated_total_points": updated_total_points,
        "previous_level": previous_level,
        "updated_level": updated_level,
        "level_up": level_up,
        "levels_gained": levels_gained,
        "progress": calculate_current_level_progress(updated_total_points),
        "message": (
            f"Você subiu para o nível {updated_level}!"
            if level_up
            else "Progresso atualizado com sucesso."
        ),
    }


def calculate_points_from_achievements(achievement_result: dict) -> int:
    """
    Soma os pontos recebidos por conquistas desbloqueadas.
    """

    return sum(
        int(achievement.get("points_reward", 0) or 0)
        for achievement in achievement_result.get("unlocked_achievements", [])
    )


def calculate_level_up(previous_points: int, updated_points: int) -> bool:
    """
    Verifica se o usuário subiu de nível comparando pontuação anterior e atual.
    """

    return calculate_level(updated_points) > calculate_level(previous_points)


def build_gamification_points_delta(
    achievement_result: dict,
    fallback_points_delta: int = 0,
) -> dict:
    """
    Define a variação de pontos a partir das conquistas ou de um valor padrão.
    """

    points_from_achievements = calculate_points_from_achievements(achievement_result)

    if points_from_achievements > 0:
        return {
            "points_delta": points_from_achievements,
            "source": "achievements",
        }

    return {
        "points_delta": int(fallback_points_delta or 0),
        "source": "fallback",
    }


def calculate_points_from_study_data(study_data: dict) -> dict:
    """
    Calcula os pontos gerados por uma sessão de estudo.

    Regra atual:
    - Toda sessão válida gera pontos base.
    - A cada 30 minutos estudados, o usuário ganha um bônus.
    - O bônus por duração possui um limite máximo para evitar pontuação exagerada.
    """

    studied_minutes = int(study_data.get("studied_minutes", 0) or 0)

    if studied_minutes < MIN_STUDY_MINUTES_TO_SCORE:
        return {
            "success": False,
            "points": 0,
            "base_points": 0,
            "duration_bonus_points": 0,
            "studied_minutes": studied_minutes,
            "completed_30_min_blocks": 0,
            "message": "Tempo de estudo inválido para pontuação.",
        }

    completed_30_min_blocks = studied_minutes // 30

    duration_bonus_points = completed_30_min_blocks * POINTS_PER_30_MINUTES
    duration_bonus_points = min(duration_bonus_points, MAX_DURATION_BONUS_POINTS)

    total_points = SESSION_COMPLETION_POINTS + duration_bonus_points

    return {
        "success": True,
        "points": total_points,
        "base_points": SESSION_COMPLETION_POINTS,
        "duration_bonus_points": duration_bonus_points,
        "studied_minutes": studied_minutes,
        "completed_30_min_blocks": completed_30_min_blocks,
        "message": "Pontos de estudo calculados com sucesso.",
    }


def calculate_progression_result(
    study_data: dict,
    previous_state: dict,
    achievement_result: dict | None = None,
) -> dict:
    """
    Recebe os dados do estudo e devolve o resultado de progressão do usuário.

    Essa função não acessa banco e não usa Streamlit.
    Ela apenas calcula:
    - pontos da sessão;
    - pontos de conquistas;
    - total atualizado;
    - nível anterior;
    - nível novo;
    - se houve level up;
    - progresso dentro do nível.
    """

    if achievement_result is None:
        achievement_result = {}

    previous_total_points = normalize_points(previous_state.get("total_points", 0))

    study_points_result = calculate_points_from_study_data(study_data)

    if not study_points_result.get("success"):
        previous_level_progression = calculate_level_progression(
            previous_total_points=previous_total_points,
            points_delta=0,
        )

        return {
            "success": False,
            "message": study_points_result.get("message"),
            "previous_total_points": previous_total_points,
            "points_delta": 0,
            "study_points": 0,
            "achievement_points": 0,
            "updated_total_points": previous_total_points,
            "previous_level": previous_level_progression["previous_level"],
            "updated_level": previous_level_progression["updated_level"],
            "level_up": False,
            "levels_gained": 0,
            "progress": previous_level_progression["progress"],
            "study_points_breakdown": {
                "base_points": 0,
                "duration_bonus_points": 0,
            },
        }

    study_points = int(study_points_result.get("points", 0) or 0)
    achievement_points = calculate_points_from_achievements(achievement_result)

    points_delta = study_points + achievement_points

    level_progression = calculate_level_progression(
        previous_total_points=previous_total_points,
        points_delta=points_delta,
    )

    return {
        "success": True,
        "message": level_progression["message"],
        "previous_total_points": level_progression["previous_total_points"],
        "points_delta": level_progression["points_delta"],
        "study_points": study_points,
        "achievement_points": achievement_points,
        "updated_total_points": level_progression["updated_total_points"],
        "previous_level": level_progression["previous_level"],
        "updated_level": level_progression["updated_level"],
        "level_up": level_progression["level_up"],
        "levels_gained": level_progression["levels_gained"],
        "progress": level_progression["progress"],
        "study_points_breakdown": {
            "base_points": study_points_result.get("base_points", 0),
            "duration_bonus_points": study_points_result.get("duration_bonus_points", 0),
        },
    }