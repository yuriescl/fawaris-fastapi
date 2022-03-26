import sqlalchemy
from databases import Database
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
from pydantic.error_wrappers import ValidationError
import fawaris

from fawaris_fastapi.sep10 import (
    new as new_sep10,
    register_routes as sep10_register_routes,
)
from fawaris_fastapi.sep24 import (
    Sep24,
    new as new_sep24,
    register_routes as sep24_register_routes,
)
from fawaris_fastapi.exception_handlers import (
    register_exception_handlers
)
from fawaris_fastapi.tables import metadata
from fawaris_fastapi import settings

app = FastAPI()

database = Database(settings.ASYNC_DATABASE_URL)

sep10 = new_sep10()
sep24 = new_sep24(database)

register_exception_handlers(app)
sep10_register_routes(app, sep10)
sep24_register_routes(app, sep24)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
