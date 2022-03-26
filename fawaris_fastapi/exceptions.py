from pydantic.error_wrappers import ValidationError

class RequestValidationError(ValidationError):
    def __init__(self, validation_error: ValidationError):
        super().__init__(validation_error.raw_errors, validation_error.model)
