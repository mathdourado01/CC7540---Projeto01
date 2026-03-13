import streamlit as st
from services.auth_service import register_user, login_user, logout_user
from utils.validators import validate_signup_form, validate_login_form

st.set_page_config(page_title="StudyRats", page_icon="🐭", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "user_name" not in st.session_state:
    st.session_state.user_name = None

st.title("StudyRats")

if st.session_state.authenticated:
    st.success("Você está logado no StudyRats.")
    st.subheader("Dashboard")
    st.write("Dashboard placeholder")
    st.info("Essa tela ainda será implementada nas próximas partes.")
    st.write(f"**Usuário:** {st.session_state.user_email}")

    if st.button("Sair"):
        logout_user()
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.rerun()

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
                success, message, user = login_user(login_email, login_password)

                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.session_state.user_name = user.user_metadata.get("name") if user.user_metadata else None
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
