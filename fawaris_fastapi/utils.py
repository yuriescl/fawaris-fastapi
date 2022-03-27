import asyncio
import codecs
import time
from typing import Optional, Union, Dict
from typing_extensions import Literal
from fastapi import Request
from stellar_sdk import ServerAsync, Keypair, TransactionBuilder, Asset, Claimant
from stellar_sdk.xdr import TransactionResult, OperationType
from pydantic.error_wrappers import ValidationError
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk import TextMemo, IdMemo, HashMemo
import fawaris

from fawaris_fastapi.exceptions import RequestValidationError

class AuthenticatedRequest(Request):
    token = None

def authenticate(jwt_secret: str):
    def wrapper(request: AuthenticatedRequest):
        # TODO handle invalid authorization format
        encoded_jwt = request.headers.get("authorization").split(" ")[1]
        request.token = fawaris.Sep10Token(encoded_jwt, jwt_secret)
        return request
    return wrapper

def validate_request_data(data, model_class):
    try:
        return model_class(**data)
    except ValidationError as e:
        raise RequestValidationError(e)


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

async def stellar_send_payment(
    source_secret: str,
    horizon_url: str,
    network_passphrase: str,
    destination_account: str,
    amount: str,
    asset_code: str,
    asset_issuer: Optional[str] = None,
    base_fee: Optional[int] = None,
    memo: Optional[Union[str, bytes, int]] = None,
    memo_type: Optional[Literal["text", "hash", "id"]] = None,
    timeout: Optional[int] = 30,
):
    if memo is not None and memo_type is None:
        raise ValueError("'memo_type' is required if 'memo' is set")
    source_kp = Keypair.from_secret(source_secret)
    async with ServerAsync(
        horizon_url=horizon_url, client=AiohttpClient()
    ) as server:
        coroutines = [server.load_account(source_kp.public_key)]
        if base_fee is None:
            coroutines.append(server.fetch_base_fee())
        results = await asyncio.gather(*coroutines)
        source_account = results[0]
        if base_fee is None:
            base_fee = results[1]
        builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        now = int(time.time())
        builder.add_time_bounds(now - 600, now + timeout)
        asset = Asset(
            code=asset_code, issuer=asset_issuer
        )
        builder.append_payment_op(
            destination=destination_account,
            asset=asset,
            amount=amount,
            source=source_kp.public_key,
        )
        if memo is not None:
            builder.add_memo(make_memo(memo, memo_type))
        envelope = builder.build()
        envelope.sign(source_kp)
        return await server.submit_transaction(envelope)

async def stellar_create_claimable_balance(
    source_secret: str,
    horizon_url: str,
    network_passphrase: str,
    destination_account: str,
    amount: str,
    asset_code: str,
    asset_issuer: Optional[str] = None,
    base_fee: Optional[int] = None,
    memo: Optional[Union[str, bytes, int]] = None,
    memo_type: Optional[Literal["text", "hash", "id"]] = None,
    timeout: Optional[int] = 30,
):
    if memo is not None and memo_type is None:
        raise ValueError("'memo_type' is required if 'memo' is set")
    source_kp = Keypair.from_secret(source_secret)
    async with ServerAsync(
        horizon_url=horizon_url, client=AiohttpClient()
    ) as server:
        coroutines = [server.load_account(source_kp.public_key)]
        if base_fee is None:
            coroutines.append(server.fetch_base_fee())
        results = await asyncio.gather(*coroutines)
        source_account = results[0]
        if base_fee is None:
            base_fee = results[1]
        builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        now = int(time.time())
        builder.add_time_bounds(now - 600, now + timeout)
        claimant = Claimant(destination=destination_account)
        asset = Asset(
            code=asset_code, issuer=asset_issuer
        )
        builder.append_create_claimable_balance_op(
            claimants=[claimant],
            asset=asset,
            amount=amount,
            source=source_kp.public_key,
        )
        if memo is not None:
            builder.add_memo(make_memo(memo, memo_type))
        envelope = builder.build()
        envelope.sign(source_kp)
        return await server.submit_transaction(envelope)

def make_memo(memo: str, memo_type: str) -> Optional[Union[TextMemo, HashMemo, IdMemo]]:
    if not (memo or memo_type):
        return None
    if memo_type == "id":
        return IdMemo(int(memo))
    elif memo_type == "hash":
        return HashMemo(memo_base64_to_hex(memo))
    elif memo_type == "text":
        return TextMemo(memo)
    else:
        raise ValueError(f"Invalid memo_type: {memo_type}")

def memo_base64_to_hex(memo):
    return (
        codecs.encode(codecs.decode(memo.encode(), "base64"), "hex").decode("utf-8")
    ).strip()

async def fetch_account(horizon_url: str, account: str) -> dict:
    async with ServerAsync(
        horizon_url=horizon_url, client=AiohttpClient()
    ) as server:
        return await server.accounts().account_id(account).call()

def is_pending_trust(account_dict: dict, asset_code: str, asset_issuer: str):
    pending_trust = True
    for balance in account_dict["balances"]:
        if balance.get("asset_type") in ["native", "liquidity_pool_shares"]:
            continue
        if (
            asset_code == balance["asset_code"]
            and asset_issuer == balance["asset_issuer"]
        ):
            pending_trust = False
            break
    return pending_trust

def get_claimable_balance_id(horizon_response: dict) -> Optional[str]:
    result_xdr = horizon_response["result_xdr"]
    balance_id_hex = None
    for op_result in TransactionResult.from_xdr(result_xdr).result.results:
        if op_result.tr.type == OperationType.CREATE_CLAIMABLE_BALANCE:
            balance_id_hex = (
                op_result.tr.create_claimable_balance_result.balance_id.to_xdr_bytes().hex()
            )
    return balance_id_hex
