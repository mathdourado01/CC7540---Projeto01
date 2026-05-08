import re

from services.supabase_client import get_supabase_client


def register_user(name: str, email: str, password: str, is_private: bool) -> tuple[bool, str]:
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "is_private": is_private
                    }
                },
            }
        )

        if response and response.user and response.session:
            return True, "Cadastro realizado com sucesso."

        return False, "Não foi possível concluir o cadastro. Verifique se o e-mail já está em uso."

    except Exception as e:
        error_message = str(e).lower()

        if "user already registered" in error_message or "already registered" in error_message:
            return False, "Já existe uma conta cadastrada com esse e-mail."

        if "email rate limit exceeded" in error_message:
            return False, "Muitas tentativas de cadastro em pouco tempo. Aguarde um pouco e tente novamente."

        return False, f"Erro ao cadastrar usuário: {e}"


def login_user(email: str, password: str) -> tuple[bool, str, object | None, object | None]:
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        if response and response.user and response.session:
            return True, "Login realizado com sucesso.", response.user, response.session

        return False, "Não foi possível realizar o login.", None, None

    except Exception as e:
        error_message = str(e).lower()

        if "invalid login credentials" in error_message:
            return False, "E-mail ou senha inválidos.", None, None

        return False, f"Erro ao fazer login: {e}", None, None


def request_password_recovery(email: str) -> tuple[bool, str]:
    """
    Fluxo simples de recuperação de senha para apresentação.

    Por segurança, o sistema não exibe senhas salvas na tela.
    A senha do usuário também não é recuperável pelo Supabase Auth em texto puro.

    Este fluxo apenas valida o e-mail informado e orienta o usuário a solicitar
    a redefinição da senha ao administrador do sistema.
    """

    normalized_email = (email or "").strip().lower()

    if not normalized_email:
        return False, "Informe o e-mail cadastrado para solicitar a recuperação de senha."

    email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    if not re.match(email_pattern, normalized_email):
        return False, "Digite um e-mail válido."

    return (
        True,
        (
            "Solicitação de recuperação registrada. "
            "Por segurança, não é possível exibir a senha salva na tela. "
            "Se este e-mail estiver cadastrado no StudyRats, solicite ao administrador "
            "do sistema a redefinição da senha."
        ),
    )


def logout_user() -> None:
    supabase = get_supabase_client()
    supabase.auth.sign_out()