import streamlit as st

from services.auth_service import register_user
from utils.validators import validate_signup_form

st.set_page_config(page_title="StudyRats", page_icon="🐭", layout="centered")

if "signup_success" not in st.session_state:
    st.session_state.signup_success = False

st.title("StudyRats")

if st.session_state.signup_success:
    st.success("Cadastro concluído com sucesso!")
    st.subheader("Próxima etapa")
    st.write("Configuração inicial das disciplinas (placeholder)")
    st.info("Essa tela ainda será implementada.")
else:
    st.header("Criar conta")

    with st.form("signup_form"):
        name = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar senha", type="password")
        is_private = st.checkbox("Quero aparecer como 'Rato Estudioso' no ranking")

        submitted = st.form_submit_button("Cadastrar")

    if submitted:
        errors = validate_signup_form(name, email, password, confirm_password)

        if errors:
            for error in errors:
                st.error(error)
        else:
            success, message = register_user(name, email, password, is_private)

            if success:
                st.session_state.signup_success = True
                st.rerun()
            else:
                st.error(message)
