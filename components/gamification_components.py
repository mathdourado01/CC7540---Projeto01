import streamlit as st


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default

        return int(value)
    except (TypeError, ValueError):
        return default


def _get_nested(data: dict, keys: list[str], default=None):
    current = data or {}

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def build_standard_gamification_payload(gamification_result: dict | None) -> dict:
    """
    Prepara um payload padronizado para o front-end consumir.

    O objetivo é impedir que o app precise conhecer todos os detalhes internos do
    processamento de gamificação. A interface passa a consumir sempre este formato:

    {
        success,
        should_show,
        points,
        level,
        achievements,
        messages,
        raw
    }
    """

    gamification_result = gamification_result or {}

    achievement_result = gamification_result.get("achievements") or {}
    unlocked_achievements = achievement_result.get("unlocked_achievements") or []

    gamification_data = gamification_result.get("gamification") or {}
    gamification_state = gamification_data.get("state") or {}
    gamification_event = gamification_data.get("event") or {}

    points_earned = _safe_int(gamification_result.get("points_earned"), 0)
    total_points = _safe_int(
        gamification_data.get(
            "total_points",
            gamification_state.get("total_points", 0),
        ),
        0,
    )

    current_level = _safe_int(
        gamification_data.get(
            "level",
            gamification_state.get("level", 1),
        ),
        1,
    )

    level_before = _safe_int(gamification_event.get("level_before"), current_level)
    level_after = _safe_int(gamification_event.get("level_after"), current_level)
    level_up = bool(
        gamification_data.get("level_up")
        or gamification_event.get("level_up")
        or level_after > level_before
    )

    current_level_progress = gamification_data.get("current_level_progress") or {}
    points_to_next_level = _safe_int(
        gamification_data.get(
            "points_to_next_level",
            gamification_state.get("points_to_next_level", 100),
        ),
        100,
    )

    feedback = gamification_result.get("feedback") or {}
    feedback_message = feedback.get("message") or gamification_result.get("message")

    has_new_achievements = bool(
        gamification_result.get("has_new_achievements")
        or achievement_result.get("has_new_achievements")
        or len(unlocked_achievements) > 0
    )

    event_already_processed = bool(
        gamification_data.get("event_already_processed")
        or gamification_result.get("gamification_already_processed")
    )

    should_show_points = bool(points_earned > 0 and not event_already_processed)
    should_show_level_up = bool(level_up and not event_already_processed)
    should_show_achievements = bool(has_new_achievements and not event_already_processed)

    should_show = bool(
        gamification_result.get("success", False)
        and (
            should_show_points
            or should_show_level_up
            or should_show_achievements
        )
    )

    achievements = []
    for achievement in unlocked_achievements:
        achievements.append(
            {
                "id": achievement.get("id") or achievement.get("achievement_id"),
                "code": achievement.get("code"),
                "title": achievement.get("title", "Conquista desbloqueada"),
                "description": achievement.get("description", ""),
                "points_reward": _safe_int(achievement.get("points_reward"), 0),
                "icon": achievement.get("icon") or "🏆",
            }
        )

    return {
        "success": bool(gamification_result.get("success", False)),
        "should_show": should_show,
        "event_already_processed": event_already_processed,
        "points": {
            "earned": points_earned,
            "total": total_points,
            "points_to_next_level": points_to_next_level,
            "current_level_progress": current_level_progress,
            "should_show": should_show_points,
        },
        "level": {
            "current": current_level,
            "before": level_before,
            "after": level_after,
            "level_up": level_up,
            "should_show": should_show_level_up,
        },
        "achievements": {
            "items": achievements,
            "total_unlocked_now": len(achievements),
            "has_new": has_new_achievements,
            "should_show": should_show_achievements,
        },
        "messages": {
            "feedback_type": feedback.get("type", "success"),
            "feedback": feedback_message,
            "processing": gamification_result.get("message"),
        },
        "raw": gamification_result,
    }


def render_gamification_styles():
    """
    CSS dos componentes visuais de gamificação.
    """

    st.markdown(
        """
        <style>
        .gamification-card {
            border-radius: 18px;
            padding: 18px 20px;
            border: 1px solid rgba(27, 94, 32, 0.18);
            box-shadow: 0 3px 10px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }

        .gamification-card-points {
            background: linear-gradient(135deg, #E8F5E9 0%, #F1FFF4 100%);
        }

        .gamification-card-level {
            background: linear-gradient(135deg, #FFF8E1 0%, #FFF1C2 100%);
            border-color: rgba(183, 135, 0, 0.24);
        }

        .gamification-card-achievement {
            background: linear-gradient(135deg, #F3E5F5 0%, #FDF4FF 100%);
            border-color: rgba(106, 27, 154, 0.22);
        }

        .gamification-kicker {
            font-size: 0.82rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #1B5E20;
            margin-bottom: 4px;
        }

        .gamification-card-level .gamification-kicker {
            color: #7A5600;
        }

        .gamification-card-achievement .gamification-kicker {
            color: #6A1B9A;
        }

        .gamification-title {
            font-size: 1.25rem;
            font-weight: 850;
            color: #0F3D22;
            margin-bottom: 5px;
        }

        .gamification-card-level .gamification-title {
            color: #5D4200;
        }

        .gamification-card-achievement .gamification-title {
            color: #4A155F;
        }

        .gamification-description {
            font-size: 0.96rem;
            color: #36513B;
            margin-bottom: 8px;
        }

        .gamification-card-level .gamification-description {
            color: #6D4C00;
        }

        .gamification-card-achievement .gamification-description {
            color: #5E356D;
        }

        .gamification-big-number {
            font-size: 2.1rem;
            line-height: 1;
            font-weight: 900;
            color: #1B5E20;
            margin-top: 4px;
        }

        .gamification-card-level .gamification-big-number {
            color: #8D6500;
        }

        .gamification-muted {
            font-size: 0.88rem;
            color: #5E6F61;
        }

        .gamification-achievement-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 10px;
        }

        .gamification-achievement-item {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(106, 27, 154, 0.16);
            border-radius: 14px;
            padding: 12px 14px;
        }

        .gamification-achievement-title {
            font-weight: 800;
            color: #4A155F;
            margin-bottom: 3px;
        }

        .gamification-progress-container {
            width: 100%;
            height: 12px;
            background: rgba(27, 94, 32, 0.12);
            border-radius: 999px;
            overflow: hidden;
            margin-top: 10px;
            margin-bottom: 6px;
        }

        .gamification-progress-bar {
            height: 12px;
            background: #2E7D32;
            border-radius: 999px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_points_earned_component(points_payload: dict):
    """
    Exibe o componente visual de pontos ganhos.
    """

    points_payload = points_payload or {}

    points_earned = _safe_int(points_payload.get("earned"), 0)
    total_points = _safe_int(points_payload.get("total"), 0)
    points_to_next_level = _safe_int(points_payload.get("points_to_next_level"), 0)
    current_level_progress = points_payload.get("current_level_progress") or {}

    progress_percentage = _safe_int(
        current_level_progress.get("progress_percentage"),
        0,
    )
    progress_percentage = max(0, min(progress_percentage, 100))

    if points_earned <= 0:
        return

    st.markdown(
        f"""
        <div class="gamification-card gamification-card-points">
            <div class="gamification-kicker">Pontos ganhos</div>
            <div class="gamification-title">+{points_earned} pontos adicionados ao seu progresso</div>
            <div class="gamification-description">
                Você agora possui <strong>{total_points} pontos</strong> acumulados.
            </div>
            <div class="gamification-progress-container">
                <div class="gamification-progress-bar" style="width: {progress_percentage}%;"></div>
            </div>
            <div class="gamification-muted">
                Faltam {points_to_next_level} pontos para o próximo nível.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_level_up_component(level_payload: dict):
    """
    Exibe o componente visual de subida de nível.
    """

    level_payload = level_payload or {}

    if not level_payload.get("level_up"):
        return

    level_before = _safe_int(level_payload.get("before"), 1)
    level_after = _safe_int(level_payload.get("after"), level_payload.get("current", 1))

    st.markdown(
        f"""
        <div class="gamification-card gamification-card-level">
            <div class="gamification-kicker">Subida de nível</div>
            <div class="gamification-title">🚀 Você subiu de nível!</div>
            <div class="gamification-description">
                Seu nível avançou de <strong>{level_before}</strong> para <strong>{level_after}</strong>.
            </div>
            <div class="gamification-big-number">Nível {level_after}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_unlocked_achievements_component(achievements_payload: dict):
    """
    Exibe o componente visual de conquistas desbloqueadas.
    """

    achievements_payload = achievements_payload or {}
    achievements = achievements_payload.get("items") or []

    if not achievements:
        return

    achievement_items_html = ""

    for achievement in achievements:
        icon = achievement.get("icon") or "🏆"
        title = achievement.get("title") or "Conquista desbloqueada"
        description = achievement.get("description") or ""
        points_reward = _safe_int(achievement.get("points_reward"), 0)

        achievement_items_html += f"""
        <div class="gamification-achievement-item">
            <div class="gamification-achievement-title">{icon} {title}</div>
            <div class="gamification-description">{description}</div>
            <div class="gamification-muted">Recompensa: +{points_reward} pontos</div>
        </div>
        """

    total_unlocked_now = len(achievements)
    achievement_label = "conquista desbloqueada" if total_unlocked_now == 1 else "conquistas desbloqueadas"

    st.markdown(
        f"""
        <div class="gamification-card gamification-card-achievement">
            <div class="gamification-kicker">Conquista desbloqueada</div>
            <div class="gamification-title">🏆 {total_unlocked_now} {achievement_label}</div>
            <div class="gamification-description">
                Você bateu uma ou mais metas de estudo e liberou novas conquistas.
            </div>
            <div class="gamification-achievement-list">
                {achievement_items_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_standard_gamification_payload(payload: dict | None):
    """
    Renderiza todos os componentes visuais a partir do payload padrão.

    Essa função é o ponto principal para o front-end consumir a gamificação.
    """

    payload = payload or {}

    if not payload.get("should_show"):
        return

    render_gamification_styles()

    render_level_up_component(payload.get("level", {}))
    render_unlocked_achievements_component(payload.get("achievements", {}))
    render_points_earned_component(payload.get("points", {}))


def render_gamification_payload_from_result(gamification_result: dict | None):
    """
    Atalho para receber o retorno bruto do processamento e renderizar o payload
    visual padronizado.
    """

    payload = build_standard_gamification_payload(gamification_result)
    render_standard_gamification_payload(payload)
    return payload