from fastapi import FastAPI
from pydantic.error_wrappers import ValidationError
from fastapi.responses import JSONResponse

import fawaris

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(Exception)
    async def exception_handler(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=500)

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        msg = str(exc)
        if isinstance(exc, ValidationError):
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

