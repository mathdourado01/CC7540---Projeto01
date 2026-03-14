import streamlit as st
import pandas as pd

from services.auth_service import register_user, login_user, logout_user
from services.dashboard_service import get_study_history, calculate_dashboard_metrics
from utils.validators import validate_signup_form, validate_login_form

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
    st.subheader("Dashboard de Estudos")
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

    try:
        history = get_study_history(
            st.session_state.user_id,
            st.session_state.access_token,
            st.session_state.refresh_token,
        )

        metrics = calculate_dashboard_metrics(history)

        if not history:
            st.info("Você ainda não possui sessões de estudo registradas.")
            st.write("Assim que houver registros, o painel exibirá métricas e histórico.")
        else:
            metric_col1, metric_col2, metric_col3 = st.columns(3)

            with metric_col1:
                st.metric("Sessões registradas", metrics["total_sessions"])

            with metric_col2:
                st.metric("Tempo total estudado", f'{metrics["total_hours"]} h')

            with metric_col3:
                st.metric("Tempo total em minutos", f'{metrics["total_minutes"]} min')

            st.markdown("### Tempo por disciplina")
            if metrics["subject_table"].empty:
                st.info("Ainda não há dados suficientes por disciplina.")
            else:
                st.dataframe(metrics["subject_table"], use_container_width=True, hide_index=True)

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
