import sqlalchemy
from databases import Database
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
from pydantic.error_wrappers import ValidationError
import fawaris

from fawaris_fastapi import Sep10, Sep24, metadata, settings
from fawaris_fastapi.exception_handlers import (
    register_exception_handlers
)

app = FastAPI()

database = Database(settings.ASYNC_DATABASE_URL)

sep10 = Sep10.new_instance()
sep24 = Sep24.new_instance(database)

register_exception_handlers(app)
sep10.register_routes(app)
sep24.register_routes(app)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
