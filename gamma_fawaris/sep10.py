from fastapi import Request
import fawaris

from gamma_fawaris.utils import detect_and_get_request_data

def register_routes(app, sep10_obj: fawaris.Sep10):
    @app.get("/auth")
    async def http_get(request: Request):
        params = dict(request.query_params)
        if not params.get("home_domain"):
            params["home_domain"] = "localhost"
        return await sep10_obj.http_get(fawaris.Sep10GetRequest(**params))

    @app.post("/auth")
    async def http_post(request: Request):
        data = await detect_and_get_request_data(request, allowed_content_types=[
            "application/x-www-form-urlencoded", "application/json"
        ])
        return await sep10_obj.http_post(fawaris.Sep10PostRequest(**data))
