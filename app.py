import streamlit as st
import pandas as pd
from datetime import date

from services.auth_service import register_user, login_user, logout_user
from services.dashboard_service import get_study_history, calculate_dashboard_metrics
from services.study_session_service import register_study_session
from services.user_subject_service import get_user_subjects
from services.ranking_service import get_basic_ranking, get_user_position, paginate_rows
from utils.validators import (
    validate_signup_form,
    validate_login_form,
    validate_study_session_form,
)

st.set_page_config(page_title="StudyRats", page_icon="🐭", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

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

st.title("StudyRats")

if st.session_state.authenticated:
    st.subheader("Área do usuário")
    st.write(f"Bem-vindo, **{st.session_state.user_email}**")

    col_logout, _ = st.columns([1, 5])
    with col_logout:
        if st.button("Sair"):
            logout_user()
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.rerun()

    dashboard_tab, session_tab, ranking_tab = st.tabs(["Dashboard", "Registrar estudo", "Ranking do grupo"])

    with dashboard_tab:
        try:
            history = get_study_history(
                st.session_state.user_id,
                st.session_state.access_token,
                st.session_state.refresh_token,
            )

            metrics = calculate_dashboard_metrics(history)

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

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.markdown("### Horas totais por dia")
                    if metrics["daily_chart"].empty:
                        st.info("Ainda não há dados suficientes para o gráfico de horas totais.")
                    else:
                        st.bar_chart(
                            metrics["daily_chart"],
                            x="Data",
                            y="Horas",
                            use_container_width=True,
                        )

                with chart_col2:
                    st.markdown("### Tempo por disciplina")
                    if metrics["subject_chart"].empty:
                        st.info("Ainda não há dados suficientes para o gráfico por disciplina.")
                    else:
                        st.bar_chart(
                            metrics["subject_chart"],
                            x="Disciplina",
                            y="Horas",
                            use_container_width=True,
                        )

                st.markdown("### Histórico de estudos")

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

        except Exception as e:
            st.error("Não foi possível carregar o dashboard.")
            st.exception(e)

    with session_tab:
        st.header("Registrar sessão de estudo")

        user_subjects = get_user_subjects(
            st.session_state.user_id,
            st.session_state.access_token,
            st.session_state.refresh_token,
        )

        if user_subjects:
            subject_mode = st.radio(
                "Como deseja informar a disciplina?",
                ["Selecionar disciplina já usada", "Digitar nova disciplina"],
                horizontal=True,
            )
        else:
            subject_mode = "Digitar nova disciplina"
            st.info("Você ainda não possui disciplinas anteriores. Digite a disciplina manualmente.")

        with st.form("study_session_form"):
            if user_subjects and subject_mode == "Selecionar disciplina já usada":
                subject_name = st.selectbox("Disciplina", user_subjects)
            else:
                subject_name = st.text_input("Disciplina")

            studied_at = st.date_input("Data do estudo", value=date.today())
            studied_minutes = st.number_input(
                "Tempo estudado (em minutos)",
                min_value=1,
                step=1,
                value=60,
            )
            save_session_submitted = st.form_submit_button("Salvar sessão")

        if save_session_submitted:
            errors = validate_study_session_form(subject_name, studied_at, int(studied_minutes))

            if errors:
                for error in errors:
                    st.error(error)
            else:
                success, message = register_study_session(
                    user_id=st.session_state.user_id,
                    access_token=st.session_state.access_token,
                    refresh_token=st.session_state.refresh_token,
                    subject_name=subject_name,
                    studied_at=studied_at,
                    studied_minutes=int(studied_minutes),
                )

                if success:
                    get_user_subjects.clear()
                    get_study_history.clear()
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with ranking_tab:
        st.header("Ranking do grupo")

        try:
            ranking_rows = get_basic_ranking(
                st.session_state.access_token,
                st.session_state.refresh_token,
            )

            if not ranking_rows:
                st.info("Ainda não há participantes ou dados suficientes para exibir o ranking.")
            else:
                metric_col1, metric_col2 = st.columns(2)

                with metric_col1:
                    st.metric("Participantes", len(ranking_rows))

                with metric_col2:
                    user_position = get_user_position(ranking_rows, st.session_state.user_id)
                    st.metric("Sua posição", user_position if user_position is not None else "-")

                total_pages = max(1, (len(ranking_rows) + 9) // 10)
                selected_page = st.selectbox(
                    "Página",
                    options=list(range(1, total_pages + 1)),
                    index=0,
                    key="ranking_page",
                )

                paged_rows, _ = paginate_rows(ranking_rows, selected_page, 10)

                ranking_display = []
                for row in paged_rows:
                    ranking_display.append(
                        {
                            "Posição": row["position"],
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

else:
    tab_login, tab_signup = st.tabs(["Entrar", "Cadastrar"])

    with tab_login:
        st.header("Login")

        with st.form("login_form"):
            login_email = st.text_input("E-mail", key="login_email")
            login_password = st.text_input("Senha", type="password", key="login_password")

            login_submitted = st.form_submit_button("Entrar")

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
                    st.rerun()
                else:
                    st.error(message)

    with tab_signup:
        st.header("Criar conta")

        with st.form("signup_form"):
            name = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            confirm_password = st.text_input("Confirmar senha", type="password")
            is_private = st.checkbox("Quero aparecer como 'Rato Estudioso' no ranking")

            signup_submitted = st.form_submit_button("Cadastrar")

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
