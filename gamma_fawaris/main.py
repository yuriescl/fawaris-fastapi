import sqlalchemy
from databases import Database
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
from pydantic.error_wrappers import ValidationError
import fawaris

from gamma_fawaris.sep10 import (
    register_routes as sep10_register_routes,
)
from gamma_fawaris.sep24 import (
    Sep24,
    register_routes as sep24_register_routes,
)
from gamma_fawaris.tables import metadata
from gamma_fawaris import settings

app = FastAPI()

database = Database(settings.ASYNC_DATABASE_URL)

jwt_key = "@)wqgb)3&e6k&(l8hfm(3wt8=*_x$w@vc$4)&nbih-&2eg9dlh"
client_secret = "SBLZPFTQY74COGBRJYKC6Y3X46KDYO46BPBRZK27IXUQ73DP6IDNUB7X"
sep10 = fawaris.Sep10(
    host_url="http://localhost",
    home_domains=["localhost"],
    horizon_url="https://horizon-testnet.stellar.org",
    network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
    signing_secret="SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY",
    jwt_key=jwt_key,
)
sep24 = Sep24(sep10_jwt_key=jwt_key, database=database, asset_issuers={"USDC": "GCCGEMWASPXY4HWAJTH2BDYKYMLVOAH4K657IDLM5ZE7DGJJCY5EY53J"})

sep10_register_routes(app, sep10)
sep24_register_routes(app, sep24)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
