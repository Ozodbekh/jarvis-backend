from app.core.exceptions import ConflictError, ServiceUnavailableError, UpstreamError


class BrainBusyError(ConflictError):
    pass


class BrainFailedError(UpstreamError):
    pass


class BrainUnavailableError(ServiceUnavailableError):
    pass
