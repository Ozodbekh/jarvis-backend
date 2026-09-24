import pytest

from app.core.exceptions import ERROR_MESSAGES, AppError
from app.modules.brain.exceptions import BrainBusyError, BrainFailedError, BrainUnavailableError


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (BrainBusyError("BRAIN_BUSY"), 409),
        (BrainFailedError("BRAIN_FAILED"), 502),
        (BrainUnavailableError("BRAIN_UNAVAILABLE"), 503),
    ],
)
def test_brain_errors_have_their_status_and_message(error: AppError, status: int) -> None:
    assert error.status_code == status
    assert error.message == ERROR_MESSAGES[error.code]
