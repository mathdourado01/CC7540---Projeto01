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


def validate_create_group_form(group_name: str) -> list[str]:
    errors = []

    if not group_name.strip():
        errors.append("O nome do grupo é obrigatório.")

    if len(group_name.strip()) < 3:
        errors.append("O nome do grupo deve ter pelo menos 3 caracteres.")

    return errors


def validate_join_group_form(invite_code: str) -> list[str]:
    errors = []

    if not invite_code.strip():
        errors.append("O código do grupo é obrigatório.")

    return errors


def validate_create_subject_form(subject_name: str) -> list[str]:
    errors = []

    if not subject_name.strip():
        errors.append("O nome da disciplina é obrigatório.")

    if len(subject_name.strip()) < 2:
        errors.append("O nome da disciplina deve ter pelo menos 2 caracteres.")

    return errors


def validate_study_session_form(subject_id: str, studied_at, studied_minutes: int) -> list[str]:
    errors = []

    if not subject_id:
        errors.append("Selecione uma disciplina.")

    if studied_at is None:
        errors.append("A data do estudo é obrigatória.")

    if studied_minutes is None or int(studied_minutes) <= 0:
        errors.append("O tempo estudado deve ser maior que zero.")

    return errors
