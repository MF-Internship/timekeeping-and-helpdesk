MINIMUM_PASSWORD_LENGTH = 12


def password_rule_errors(username: str, password: str) -> tuple[str, ...]:
    errors: list[str] = []
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        errors.append("minimum_length")
    if password == username:
        errors.append("different_from_username")
    return tuple(errors)
