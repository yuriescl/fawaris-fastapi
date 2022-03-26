from fastapi import FastAPI
from pydantic.error_wrappers import ValidationError
from fastapi.responses import JSONResponse
import fawaris

from fawaris_fastapi.exceptions import RequestValidationError

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def value_error_handler(request, exc):
        msg = ""
        for error in exc.errors():
            if error["type"] == "value_error.missing":
                try:
                    field = error["loc"][0]
                    msg += f"Missing value for '{field}'"
                except (KeyError, IndexError):
                    msg += str(error) + ". "
            else:
                msg += str(error) + ". "
        return JSONResponse({"error": msg}, status_code=400)

    @app.exception_handler(fawaris.Sep10InvalidToken)
    async def sep10_invalid_token_handler(request, exc):
        return JSONResponse({"type": "authentication_required"}, status_code=403)

