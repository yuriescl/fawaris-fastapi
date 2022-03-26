from fastapi import Request
import fawaris

from fawaris_fastapi.utils import detect_and_get_request_data, validate_request_data
from fawaris_fastapi import settings

def new():
    return fawaris.Sep10(
        host_url=settings.HOST_URL,
        home_domains=settings.HOME_DOMAINS,
        horizon_url=settings.HORIZON_URL,
        network_passphrase=settings.NETWORK_PASSPHRASE,
        signing_secret=settings.SIGNING_SECRET,
        jwt_secret=settings.JWT_SECRET,
    )

def register_routes(app, sep10_obj: fawaris.Sep10):
    @app.get("/auth")
    async def http_get(request: Request):
        params = dict(request.query_params)
        if not params.get("home_domain"):
            params["home_domain"] = settings.HOME_DOMAINS[0]
        req = validate_request_data(params, fawaris.Sep10GetRequest)
        return await sep10_obj.http_get(req)

    @app.post("/auth")
    async def http_post(request: Request):
        data = await detect_and_get_request_data(request, allowed_content_types=[
            "application/x-www-form-urlencoded", "application/json"
        ])
        req = validate_request_data(data, fawaris.Sep10PostRequest)
        return await sep10_obj.http_post(req)
