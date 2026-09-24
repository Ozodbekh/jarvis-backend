from app.core.exceptions import ERROR_MESSAGES
from app.modules.vault.exceptions import VaultMissingError


def test_vault_missing_is_unavailable_with_a_message() -> None:
    error = VaultMissingError("VAULT_MISSING")

    assert error.status_code == 503
    assert error.message == ERROR_MESSAGES["VAULT_MISSING"]
