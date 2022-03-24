from fastapi import Request
import fawaris

class AuthenticatedRequest(Request):
    token = None

def authenticate(jwt_key: str):
    def wrapper(request: AuthenticatedRequest):
        # TODO handle invalid authorization format
        encoded_jwt = request.headers.get("authorization").split(" ")[1]
        request.token = fawaris.Sep10Token(encoded_jwt, jwt_key)
        return request
    return wrapper

async def detect_and_get_request_data(
    request: Request,
    allowed_content_types=[
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "application/json",
    ],
):
    content_type = request.headers.get("content-type")
    allowed = False
    for allowed_content_type in allowed_content_types:
        if allowed_content_type in content_type:
            allowed = True
    if not allowed:
        raise ValueError("Header 'Content-Type' has an invalid value")
    if "multipart/form-data" in content_type:
        data = await request.form()
    elif "application/x-www-form-urlencoded" in content_type:
        data = await request.form()
    elif "application/json" in content_type:
        data = await request.json()
    return data

