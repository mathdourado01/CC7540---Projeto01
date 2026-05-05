import streamlit as st
import pandas as pd
from datetime import date

from services.auth_service import register_user, login_user, logout_user
from services.dashboard_service import (
    get_study_history,
    calculate_dashboard_metrics,
)
from services.gamification_service import (
    generate_processing_key,
    process_study_session_with_gamification,
)
from services.streak_service import recalculate_streak_on_app_open

from services.group_service import get_user_group, create_group, join_group
from services.group_subject_service import get_group_subjects, create_group_subject
from services.ranking_service import (
    get_group_ranking,
    sort_ranking,
    get_user_position,
    paginate_rows,
)
from utils.validators import (
    validate_signup_form,
    validate_login_form,
    validate_create_group_form,
    validate_join_group_form,
    validate_create_subject_form,
    validate_study_session_form,
)

st.set_page_config(page_title="StudyRats", page_icon="🐭", layout="wide")


def apply_custom_ui():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1.5rem;
        }

        h1, h2, h3 {
            color: #1B5E20;
        }

        div[data-testid="stMetric"] {
            background: #F7FCF7;
            border: 1px solid #D7EED8;
            border-radius: 14px;
            padding: 12px;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 10px;
        }

        .section-card {
            background: #FFFFFF;
            border: 1px solid #DCEFD9;
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1B5E20;
            margin-bottom: 0.5rem;
        }

        .streak-card {
            background: linear-gradient(135deg, #FFF8E1 0%, #FFF3CD 100%);
            border: 1px solid #F6D57A;
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 3px 8px rgba(0, 0, 0, 0.05);
            margin-top: 8px;
            min-height: 132px;
        }

        .streak-card--record {
            background: linear-gradient(135deg, #E8F5E9 0%, #DDF6E4 100%);
            border: 1px solid #8ED1A0;
        }

        .streak-label {
            font-size: 0.95rem;
            font-weight: 700;
            color: #8D6E00;
            margin-bottom: 6px;
        }

        .streak-card--record .streak-label {
            color: #256D3C;
        }

        .streak-value {
            font-size: 2rem;
            font-weight: 800;
            color: #5D4037;
            line-height: 1.1;
        }

        .streak-card--record .streak-value {
            color: #1B5E20;
        }

        .streak-caption {
            font-size: 0.92rem;
            color: #6D4C41;
            margin-top: 6px;
        }

        .streak-card--record .streak-caption {
            color: #2F5D3A;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def start_card(title: str):
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )


def end_card():
    st.markdown("</div>", unsafe_allow_html=True)


def render_current_streak_component(current_streak: int):
    day_label = "dia" if current_streak == 1 else "dias"

    st.markdown(
        f"""
        <div class="streak-card">
            <div class="streak-label">🔥 Streak atual</div>
            <div class="streak-value">{current_streak} {day_label}</div>
            <div class="streak-caption">Continue estudando para manter sua sequência ativa.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_highest_streak_component(highest_streak: int):
    day_label = "dia" if highest_streak == 1 else "dias"

    st.markdown(
        f"""
        <div class="streak-card streak-card--record">
            <div class="streak-label">🏅 Maior streak alcançado</div>
            <div class="streak-value">{highest_streak} {day_label}</div>
            <div class="streak-caption">Este é o seu recorde de constância até agora.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_flash_message(message_type: str, message_text: str):
    if message_type == "success":
        st.success(message_text)
    elif message_type == "warning":
        st.warning(message_text)
    elif message_type == "error":
        st.error(message_text)
    else:
        st.info(message_text)


def _build_daily_streak_snapshot_key() -> str:
    return f"{st.session_state.user_id}:{date.today().isoformat()}"


def update_streak_state(streak_data: dict) -> dict:
    """
    Atualiza o estado da aplicação com os dados mais recentes da streak.
    """

    normalized_streak = {
        "current_streak": streak_data.get("current_streak", 0),
        "highest_streak": streak_data.get(
            "highest_streak",
            streak_data.get("longest_streak", 0),
        ),
        "longest_streak": streak_data.get(
            "longest_streak",
            streak_data.get("highest_streak", 0),
        ),
        "last_study_date": streak_data.get("last_study_date"),
        "status": streak_data.get("status"),
        "message": streak_data.get("message"),
    }

    st.session_state.persisted_streak = normalized_streak
    st.session_state.persisted_streak_loaded = True

    st.session_state.streak_snapshot_key = _build_daily_streak_snapshot_key()
    st.session_state.streak_snapshot = normalized_streak

    return normalized_streak


def load_persisted_streak_once() -> dict:
    if (
        st.session_state.persisted_streak_loaded
        and st.session_state.persisted_streak is not None
    ):
        return st.session_state.persisted_streak

    streak_data = recalculate_streak_on_app_open(
        user_id=st.session_state.user_id,
        access_token=st.session_state.access_token,
        refresh_token=st.session_state.refresh_token,
    )

    return update_streak_state(streak_data)


def update_achievement_state(achievement_result: dict) -> dict:
    """
    Atualiza o estado da aplicação com as conquistas liberadas no processamento.
    """

    unlocked_achievements = achievement_result.get("unlocked_achievements", [])

    st.session_state.unlocked_achievements = unlocked_achievements
    st.session_state.achievement_feedback = {
        "success": achievement_result.get("success", True),
        "has_new_achievements": achievement_result.get("has_new_achievements", False),
        "total_unlocked": achievement_result.get("total_unlocked", 0),
        "message": achievement_result.get("message"),
        "unlocked_achievements": unlocked_achievements,
    }

    return st.session_state.achievement_feedback


def resolve_safe_opening_streak_summary() -> dict:
    if st.session_state.dashboard_metrics_override is not None:
        override_summary = {
            "current_streak": st.session_state.dashboard_metrics_override.get("current_streak", 0),
            "highest_streak": st.session_state.dashboard_metrics_override.get("highest_streak", 0),
            "longest_streak": st.session_state.dashboard_metrics_override.get(
                "longest_streak",
                st.session_state.dashboard_metrics_override.get("highest_streak", 0),
            ),
            "last_study_date": st.session_state.dashboard_metrics_override.get("last_study_date"),
        }

        st.session_state.persisted_streak = override_summary
        st.session_state.persisted_streak_loaded = True
        st.session_state.streak_snapshot_key = _build_daily_streak_snapshot_key()
        st.session_state.streak_snapshot = override_summary

        return override_summary

    snapshot_key = _build_daily_streak_snapshot_key()

    if (
        st.session_state.streak_snapshot_key == snapshot_key
        and st.session_state.streak_snapshot is not None
    ):
        return st.session_state.streak_snapshot

    persisted_summary = load_persisted_streak_once()

    safe_summary = {
        "current_streak": persisted_summary.get("current_streak", 0),
        "highest_streak": persisted_summary.get(
            "highest_streak",
            persisted_summary.get("longest_streak", 0),
        ),
        "longest_streak": persisted_summary.get(
            "longest_streak",
            persisted_summary.get("highest_streak", 0),
        ),
        "last_study_date": persisted_summary.get("last_study_date"),
    }

    st.session_state.streak_snapshot_key = snapshot_key
    st.session_state.streak_snapshot = safe_summary

    return safe_summary


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "persisted_streak" not in st.session_state:
    st.session_state.persisted_streak = None

if "persisted_streak_loaded" not in st.session_state:
    st.session_state.persisted_streak_loaded = False

if "unlocked_achievements" not in st.session_state:
    st.session_state.unlocked_achievements = []

if "achievement_feedback" not in st.session_state:
    st.session_state.achievement_feedback = None

if "pending_study_session_processing_key" not in st.session_state:
    st.session_state.pending_study_session_processing_key = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "user_name" not in st.session_state:
    st.session_state.user_name = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

if "dashboard_metrics_override" not in st.session_state:
    st.session_state.dashboard_metrics_override = None

if "dashboard_history_override" not in st.session_state:
    st.session_state.dashboard_history_override = None

if "streak_feedback" not in st.session_state:
    st.session_state.streak_feedback = None

if "streak_snapshot_key" not in st.session_state:
    st.session_state.streak_snapshot_key = None

if "streak_snapshot" not in st.session_state:
    st.session_state.streak_snapshot = None


apply_custom_ui()

st.title("StudyRats")

if st.session_state.authenticated:
    header_col1, header_col2 = st.columns([5, 1])

    with header_col1:
        st.write(f"Bem-vindo, **{st.session_state.user_email}**")

    with header_col2:
        if st.button("Sair", use_container_width=True):
            logout_user()
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.session_state.dashboard_metrics_override = None
            st.session_state.dashboard_history_override = None
            st.session_state.streak_feedback = None
            st.session_state.streak_snapshot_key = None
            st.session_state.streak_snapshot = None
            st.session_state.persisted_streak = None
            st.session_state.persisted_streak_loaded = False
            st.session_state.unlocked_achievements = []
            st.session_state.achievement_feedback = None
            st.session_state.pending_study_session_processing_key = None
            st.rerun()

    current_group = get_user_group(
        st.session_state.user_id,
        st.session_state.access_token,
        st.session_state.refresh_token,
    )

    dashboard_tab, group_tab, subjects_tab, sessions_tab, ranking_tab = st.tabs(
        ["📊 Dashboard", "👥 Grupo", "📚 Disciplinas", "⏱️ Sessões", "🏆 Ranking"],
        default="📊 Dashboard",
        key="main_nav",
        on_change="rerun",
    )

    if dashboard_tab.open:
        with dashboard_tab:
            try:
                streak_summary = resolve_safe_opening_streak_summary()

                if (
                    st.session_state.dashboard_history_override is not None
                    and st.session_state.dashboard_metrics_override is not None
                ):
                    history = st.session_state.dashboard_history_override
                    metrics = st.session_state.dashboard_metrics_override
                else:
                    history = get_study_history(
                        st.session_state.user_id,
                        st.session_state.access_token,
                        st.session_state.refresh_token,
                    )
                    metrics = calculate_dashboard_metrics(history)

                if st.session_state.streak_feedback:
                    show_flash_message(
                        st.session_state.streak_feedback["type"],
                        st.session_state.streak_feedback["message"],
                    )
                    st.session_state.streak_feedback = None

                if st.session_state.achievement_feedback:
                    achievement_feedback = st.session_state.achievement_feedback

                    if achievement_feedback.get("has_new_achievements"):
                        st.success("🏆 Nova conquista desbloqueada!")

                        for achievement in achievement_feedback.get("unlocked_achievements", []):
                            icon = achievement.get("icon") or "🏆"
                            title = achievement.get("title", "Conquista")
                            description = achievement.get("description", "")
                            points_reward = achievement.get("points_reward", 0)

                            st.info(
                                f"{icon} **{title}**\n\n"
                                f"{description}\n\n"
                                f"+{points_reward} pontos"
                            )

                    st.session_state.achievement_feedback = None

                start_card("Seu progresso de consistência")
                streak_col_1, streak_col_2 = st.columns(2)

                with streak_col_1:
                    render_current_streak_component(streak_summary.get("current_streak", 0))

                with streak_col_2:
                    render_highest_streak_component(streak_summary.get("highest_streak", 0))
                end_card()

                st.session_state.dashboard_history_override = None
                st.session_state.dashboard_metrics_override = None

                start_card("Resumo do grupo")
                if current_group:
                    col_group_1, col_group_2 = st.columns(2)

                    with col_group_1:
                        st.success(f"Você está no grupo: **{current_group['name']}**")

                    with col_group_2:
                        st.info(f"Código do grupo: **{current_group['invite_code']}**")
                else:
                    st.info("Você ainda não participa de um grupo.")
                end_card()

                start_card("Métricas gerais")
                if not history:
                    st.info("Você ainda não possui sessões de estudo registradas.")
                    st.write("Assim que houver registros, o painel exibirá métricas, gráficos e histórico.")
                else:
                    metric_col1, metric_col2, metric_col3 = st.columns(3)

                    with metric_col1:
                        st.metric("Sessões registradas", metrics["total_sessions"])

                    with metric_col2:
                        st.metric("Tempo total estudado", f'{metrics["total_hours"]} h')

                    with metric_col3:
                        st.metric("Tempo total em minutos", f'{metrics["total_minutes"]} min')
                end_card()

                if history:
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        start_card("Horas totais por dia")
                        if metrics["daily_chart"].empty:
                            st.info("Ainda não há dados suficientes para o gráfico de horas totais.")
                        else:
                            st.bar_chart(
                                metrics["daily_chart"],
                                x="Data",
                                y="Horas",
                                use_container_width=True,
                            )
                        end_card()

                    with chart_col2:
                        start_card("Tempo por disciplina")
                        if metrics["subject_chart"].empty:
                            st.info("Ainda não há dados suficientes para o gráfico por disciplina.")
                        else:
                            st.bar_chart(
                                metrics["subject_chart"],
                                x="Disciplina",
                                y="Horas",
                                use_container_width=True,
                            )
                        end_card()

                    start_card("Histórico de estudos")
                    history_df = pd.DataFrame(history)
                    history_df = history_df.rename(
                        columns={
                            "subject_name": "Disciplina",
                            "studied_minutes": "Minutos estudados",
                            "studied_at": "Data de estudo",
                            "created_at": "Registrado em",
                        }
                    )

                    history_df = history_df[
                        ["Disciplina", "Minutos estudados", "Data de estudo", "Registrado em"]
                    ]

                    st.dataframe(history_df, use_container_width=True, hide_index=True)
                    end_card()

            except Exception as e:
                st.error("Não foi possível carregar o dashboard.")
                st.exception(e)

    if group_tab.open:
        with group_tab:
            start_card("Gerenciar grupo")
            if current_group:
                st.success(f"Você já está no grupo **{current_group['name']}**.")
                st.info(f"Código do grupo: **{current_group['invite_code']}**")
            else:
                create_tab, join_tab = st.tabs(
                    ["Criar grupo", "Entrar em grupo"],
                    key="group_nav",
                    on_change="rerun",
                )

                with create_tab:
                    with st.form("create_group_form"):
                        group_name = st.text_input("Nome do grupo")
                        create_group_submitted = st.form_submit_button("Criar grupo")

                    if create_group_submitted:
                        errors = validate_create_group_form(group_name)

                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            success, message = create_group(
                                st.session_state.user_id,
                                st.session_state.access_token,
                                st.session_state.refresh_token,
                                group_name,
                            )

                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                with join_tab:
                    with st.form("join_group_form"):
                        invite_code = st.text_input("Código do grupo").upper()
                        join_group_submitted = st.form_submit_button("Entrar no grupo")

                    if join_group_submitted:
                        errors = validate_join_group_form(invite_code)

                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            success, message = join_group(
                                st.session_state.user_id,
                                st.session_state.access_token,
                                st.session_state.refresh_token,
                                invite_code,
                            )

                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            end_card()

    if subjects_tab.open:
        with subjects_tab:
            start_card("Disciplinas do grupo")
            if not current_group:
                st.info("Crie ou entre em um grupo para gerenciar disciplinas.")
            else:
                subjects = get_group_subjects(
                    current_group["id"],
                    st.session_state.access_token,
                    st.session_state.refresh_token,
                )

                col_subject_form, col_subject_list = st.columns([1, 1.2])

                with col_subject_form:
                    with st.form("create_subject_form"):
                        subject_name = st.text_input("Nome da disciplina")
                        create_subject_submitted = st.form_submit_button("Adicionar disciplina")

                    if create_subject_submitted:
                        errors = validate_create_subject_form(subject_name)

                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            success, message = create_group_subject(
                                current_group["id"],
                                st.session_state.user_id,
                                st.session_state.access_token,
                                st.session_state.refresh_token,
                                subject_name,
                            )

                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                with col_subject_list:
                    if not subjects:
                        st.info("Ainda não há disciplinas cadastradas para este grupo.")
                    else:
                        subjects_df = pd.DataFrame(subjects)
                        subjects_df = subjects_df.rename(columns={"name": "Disciplina"})
                        st.dataframe(
                            subjects_df[["Disciplina"]],
                            use_container_width=True,
                            hide_index=True,
                        )
            end_card()

    if sessions_tab.open:
        with sessions_tab:
            start_card("Registrar sessão de estudo")
            if not current_group:
                st.info("Entre em um grupo antes de registrar suas sessões.")
            else:
                subjects = get_group_subjects(
                    current_group["id"],
                    st.session_state.access_token,
                    st.session_state.refresh_token,
                )

                if not subjects:
                    st.info("Cadastre ao menos uma disciplina para registrar sessões de estudo.")
                else:
                    subject_options = {subject["name"]: subject["id"] for subject in subjects}

                    with st.form("study_session_form"):
                        selected_subject_name = st.selectbox(
                            "Disciplina",
                            options=list(subject_options.keys()),
                        )
                        studied_at = st.date_input("Data do estudo", value=date.today())
                        studied_minutes = st.number_input(
                            "Tempo estudado (em minutos)",
                            min_value=1,
                            step=1,
                            value=60,
                        )

                        save_session_submitted = st.form_submit_button("Salvar sessão")

                    if save_session_submitted:
                        selected_subject_id = subject_options[selected_subject_name]

                        errors = validate_study_session_form(
                            selected_subject_id,
                            studied_at,
                            int(studied_minutes),
                        )

                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            previous_streak = load_persisted_streak_once()

                            if st.session_state.pending_study_session_processing_key is None:
                                st.session_state.pending_study_session_processing_key = generate_processing_key()

                            gamification_result = process_study_session_with_gamification(
                                user_id=st.session_state.user_id,
                                access_token=st.session_state.access_token,
                                refresh_token=st.session_state.refresh_token,
                                subject_id=selected_subject_id,
                                studied_at=studied_at,
                                studied_minutes=int(studied_minutes),
                                processing_key=st.session_state.pending_study_session_processing_key,
                                previous_streak=previous_streak,
                            )

                            if gamification_result.get("success"):
                                get_study_history.clear()
                                get_group_ranking.clear()

                                updated_streak_state = update_streak_state(
                                    gamification_result.get("streak", {})
                                )

                                updated_history = gamification_result.get("dashboard_history", [])
                                updated_metrics = gamification_result.get("metrics", {})

                                updated_metrics["current_streak"] = updated_streak_state.get("current_streak", 0)
                                updated_metrics["highest_streak"] = updated_streak_state.get("highest_streak", 0)
                                updated_metrics["longest_streak"] = updated_streak_state.get("longest_streak", 0)
                                updated_metrics["last_study_date"] = updated_streak_state.get("last_study_date")

                                update_achievement_state(
                                    gamification_result.get("achievements", {})
                                )

                                st.session_state.dashboard_history_override = updated_history
                                st.session_state.dashboard_metrics_override = updated_metrics

                                st.session_state.streak_feedback = {
                                    "type": gamification_result.get("feedback", {}).get("type", "success"),
                                    "message": gamification_result.get("feedback", {}).get(
                                        "message",
                                        gamification_result.get("message"),
                                    ),
                                    "status": gamification_result.get("session_status"),
                                }

                                st.session_state.pending_study_session_processing_key = None

                                st.success(gamification_result.get("message"))
                                st.rerun()
                            else:
                                st.error(gamification_result.get("message"))
            end_card()

    if ranking_tab.open:
        with ranking_tab:
            start_card("Ranking do grupo")
            if not current_group:
                st.info("Entre ou crie um grupo para visualizar o ranking.")
            else:
                col_filter_1, col_filter_2 = st.columns(2)

                with col_filter_1:
                    period_label = st.selectbox(
                        "Período do ranking",
                        options=["Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias"],
                        index=1,
                    )

                with col_filter_2:
                    ranking_mode_label = st.radio(
                        "Ordenar ranking por",
                        options=["Pontos", "Tempo"],
                        horizontal=True,
                    )

                period_days_map = {
                    "Últimos 7 dias": 7,
                    "Últimos 30 dias": 30,
                    "Últimos 90 dias": 90,
                }

                ranking_mode = "points" if ranking_mode_label == "Pontos" else "minutes"
                period_days = period_days_map[period_label]

                try:
                    ranking_rows = get_group_ranking(
                        st.session_state.access_token,
                        st.session_state.refresh_token,
                        period_days,
                    )

                    ranking_rows = sort_ranking(ranking_rows, ranking_mode)

                    if not ranking_rows:
                        st.info("Ainda não há participantes ou dados suficientes para exibir o ranking.")
                    else:
                        user_position = get_user_position(
                            ranking_rows,
                            st.session_state.user_id,
                            ranking_mode,
                        )

                        metric_rank_1, metric_rank_2, metric_rank_3 = st.columns(3)

                        current_user_row = next(
                            (row for row in ranking_rows if row["user_id"] == st.session_state.user_id),
                            None,
                        )

                        with metric_rank_1:
                            st.metric("Participantes", len(ranking_rows))

                        with metric_rank_2:
                            st.metric("Sua posição", user_position if user_position is not None else "-")

                        with metric_rank_3:
                            if ranking_mode == "points":
                                st.metric(
                                    "Seus pontos no período",
                                    current_user_row["total_points"] if current_user_row else 0,
                                )
                            else:
                                st.metric(
                                    "Seus minutos no período",
                                    current_user_row["total_minutes"] if current_user_row else 0,
                                )

                        page_size = 10
                        total_pages = max(1, (len(ranking_rows) + page_size - 1) // page_size)

                        page = st.selectbox(
                            "Página",
                            options=list(range(1, total_pages + 1)),
                            index=0,
                            key=f"ranking_page_{ranking_mode}_{period_days}",
                        )

                        paged_rows, _ = paginate_rows(ranking_rows, page, page_size)

                        ranking_display = []
                        for row in paged_rows:
                            ranking_display.append(
                                {
                                    "Posição": row["rank_by_points"] if ranking_mode == "points" else row["rank_by_minutes"],
                                    "Nome": row["display_name"],
                                    "Pontos": row["total_points"],
                                    "Minutos": row["total_minutes"],
                                    "Horas": round(row["total_minutes"] / 60, 2),
                                }
                            )

                        ranking_df = pd.DataFrame(ranking_display)
                        st.dataframe(ranking_df, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error("Não foi possível carregar o ranking do grupo.")
                    st.exception(e)
            end_card()

else:
    auth_tab_login, auth_tab_signup = st.tabs(
        ["Entrar", "Cadastrar"],
        default="Entrar",
        key="auth_nav",
        on_change="rerun",
    )

    with auth_tab_login:
        start_card("Login")
        with st.form("login_form"):
            login_email = st.text_input("E-mail", key="login_email")
            login_password = st.text_input("Senha", type="password", key="login_password")
            login_submitted = st.form_submit_button("Entrar", use_container_width=True)

        if login_submitted:
            errors = validate_login_form(login_email, login_password)

            if errors:
                for error in errors:
                    st.error(error)
            else:
                success, message, user, session = login_user(login_email, login_password)

                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.session_state.user_name = user.user_metadata.get("name") if user.user_metadata else None
                    st.session_state.access_token = session.access_token
                    st.session_state.refresh_token = session.refresh_token
                    st.session_state.main_nav = "📊 Dashboard"
                    st.session_state.streak_snapshot_key = None
                    st.session_state.streak_snapshot = None
                    st.session_state.persisted_streak = None
                    st.session_state.persisted_streak_loaded = False
                    st.session_state.unlocked_achievements = []
                    st.session_state.achievement_feedback = None
                    st.session_state.pending_study_session_processing_key = None
                    st.rerun()
                else:
                    st.error(message)
        end_card()

    with auth_tab_signup:
        start_card("Criar conta")
        with st.form("signup_form"):
            name = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            confirm_password = st.text_input("Confirmar senha", type="password")
            is_private = st.checkbox("Quero aparecer como 'Rato Estudioso' no ranking")
            signup_submitted = st.form_submit_button("Cadastrar", use_container_width=True)

        if signup_submitted:
            errors = validate_signup_form(name, email, password, confirm_password)

            if errors:
                for error in errors:
                    st.error(error)
            else:
                success, message = register_user(name, email, password, is_private)

                if success:
                    st.success(message)
                    st.info("Agora faça login na aba 'Entrar'.")
                else:
                    st.error(message)
        end_card()