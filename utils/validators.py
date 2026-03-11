import re


def validate_signup_form(name: str, email: str, password: str, confirm_password: str) -> list[str]:
    errors = []

    if not name.strip():
        errors.append("O nome é obrigatório.")

    if not email.strip():
        errors.append("O e-mail é obrigatório.")
    else:
        email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(email_pattern, email):
            errors.append("Digite um e-mail válido.")

    if not password:
        errors.append("A senha é obrigatória.")

    if not confirm_password:
        errors.append("A confirmação de senha é obrigatória.")

    if password and confirm_password and password != confirm_password:
        errors.append("A senha e a confirmação de senha precisam ser iguais.")

    if password and len(password) < 6:
        errors.append("A senha deve ter pelo menos 6 caracteres.")

    return errors


def validate_login_form(email: str, password: str) -> list[str]:
    errors = []

    if not email.strip():
        errors.append("O e-mail é obrigatório.")

    if not password:
        errors.append("A senha é obrigatória.")

    return errors