import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Callable, Any, Optional, Union, Dict
from pydantic import Field
from databases import Database
from fastapi import Depends, Request
from overrides import overrides
from abc import ABC, abstractmethod
import fawaris

from fawaris_fastapi import tables
from fawaris_fastapi.utils import (
    authenticate,
    detect_and_get_request_data,
    fetch_account,
    is_pending_trust,
    stellar_create_claimable_balance,
    stellar_send_payment,
    get_claimable_balance_id,
    validate_request_data,
)


def register_routes(app, sep24_obj: fawaris.Sep24):
    @app.post("/sep24/transactions/deposit/interactive")
    async def http_post_transactions_deposit_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        req = validate_request_data(data, fawaris.Sep24DepositPostRequest)
        return await sep24_obj.http_post_transactions_deposit_interactive(
            req, request.token
        )

    @app.post("/sep24/transactions/withdraw/interactive")
    async def http_post_transactions_withdraw_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        req = validate_request_data(data, fawaris.Sep24WithdrawPostRequest)
        return await sep24_obj.http_post_transactions_withdraw_interactive(
            req, request.token
        )

    @app.get("/sep24/info")
    async def http_get_info(request: Request):
        req = validate_request_data(dict(request.query_params), fawaris.Sep24InfoRequest)
        return await sep24_obj.http_get_info(req)

    @app.get("/sep24/transactions")
    async def http_get_transactions(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        req = validate_request_data(dict(request.query_params), fawaris.Sep24TransactionsGetRequest)
        return await sep24_obj.http_get_transactions(req, request.token)

    @app.get("/sep24/transaction")
    async def http_get_transaction(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        req = validate_request_data(dict(request.query_params), fawaris.Sep24TransactionGetRequest)
        return await sep24_obj.http_get_transaction(req, request.token)


class Sep24Transaction(fawaris.Sep24Transaction):
    asset: fawaris.Asset = Field(..., exclude=True)
    paging_token: Optional[str] = Field(None, exclude=True)
    claimable_balance_supported: Optional[str] = Field(None, exclude=True)


class Sep24(fawaris.Sep24):
    sep10_jwt_key: str
    distribution_secret: str
    database: Database
    log: Callable[[str], Any]
    assets: Dict[str, fawaris.Asset]

    def __init__(
        self,
        sep10_jwt_key: str,
        distribution_secret: str,
        database: Database,
        assets: Dict[str, fawaris.Asset],
        log: Optional[Callable[[str], Any]] = lambda msg: None,
    ):
        self.sep10_jwt_key = sep10_jwt_key
        self.distribution_secret = distribution_secret
        self.database = database
        self.assets = assets
        self.log = log

    async def http_post_transactions_deposit_interactive(
        self, request: fawaris.Sep24DepositPostRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24PostResponse:
        info = await self.http_get_info(fawaris.Sep24InfoRequest(lang=request.lang))
        try:
            if not info["deposit"][request.asset_code].enabled:
                raise KeyError()
        except KeyError:
            raise ValueError(f"Deposit is not enabled for asset {request.asset_code}")
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return fawaris.Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def http_post_transactions_withdraw_interactive(
        self, request: fawaris.Sep24WithdrawPostRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24PostResponse:
        info = await self.http_get_info(fawaris.Sep24InfoRequest(lang=request.lang))
        try:
            if not info["withdraw"][request.asset_code].enabled:
                raise KeyError()
        except KeyError:
            raise ValueError(f"Withdrawal is not enabled for asset {request.asset_code}")
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return fawaris.Sep24PostResponse(
            url=url,
            id=tx.id,
        )


    @overrides
    async def http_get_fee(
        self,
        request: fawaris.Sep24FeeRequest,
        token: Optional[fawaris.Sep10Token] = None,
    ) -> fawaris.Sep24FeeResponse:
        raise NotImplementedError()

    @overrides
    async def http_get_transactions(
        self, request: fawaris.Sep24TransactionsGetRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24TransactionsGetResponse:
        query = tables.sep24_transactions.select()
        if request.asset_code is not None:
            query = query.where(tables.sep24_transactions.c.asset_code == request.asset_code)
        transactions = []
        async for row in self.database.iterate(query):
            transactions.append(self.row_to_transaction(row))
        return transactions

    @overrides
    async def http_get_transaction(
        self, request: fawaris.Sep24TransactionGetRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24TransactionGetResponse:
        raise NotImplementedError()

    @overrides
    async def create_transaction(
        self,
        request: Union[
            fawaris.Sep24DepositPostRequest, fawaris.Sep24WithdrawPostRequest
        ],
        token: fawaris.Sep10Token,
    ) -> Sep24Transaction:
        if isinstance(request, fawaris.Sep24DepositPostRequest):
            kind = "deposit"
        if isinstance(request, fawaris.Sep24WithdrawPostRequest):
            kind = "withdrawal"
        query = tables.sep24_transactions.insert()
        transaction = Sep24Transaction(
            id=str(uuid.uuid4()),  # TODO make sure it's unique
            kind=kind,
            status="pending_user_transfer_start",
            asset=self.assets[request.asset_code],
        )
        values = self.transaction_to_values(transaction)
        await self.database.execute(query=query, values=values)
        return transaction

    @overrides
    async def get_interactive_url(
        self,
        request: Union[
            fawaris.Sep24DepositPostRequest, fawaris.Sep24WithdrawPostRequest
        ],
        token: fawaris.Sep10Token,
        tx: fawaris.Sep24Transaction,
    ) -> str:
        return "https://sep24.mydomain.com"

    @overrides
    async def get_transactions(
        self,
        kind=None,
        status=None,
        memo=None,
        withdraw_anchor_account=None,
    ) -> List[fawaris.Sep24Transaction]:
        query = tables.sep24_transactions.select()
        if kind is not None:
            query = query.where(tables.sep24_transactions.c.kind == kind)
        if status is not None:
            query = query.where(tables.sep24_transactions.c.status == status)
        if memo is not None:
            query = query.where(tables.sep24_transactions.c.memo == memo)
        if withdraw_anchor_account is not None:
            query = query.where(
                tables.sep24_transactions.c.withdraw_anchor_account
                == withdraw_anchor_account
            )
        transactions = []
        async for row in self.database.iterate(query):
            transactions.append(self.row_to_transaction(row))
        return transactions

    @overrides
    async def get_transaction_asset(
        self, transaction: fawaris.Sep24Transaction
    ) -> fawaris.Asset:
        return transaction.asset


    @overrides
    async def process_withdrawal_received(self,
        transaction: fawaris.Sep24Transaction,
        amount_received: str,
        from_address: str,
        horizon_response: Dict,
    ):
        if Decimal(amount_received) != Decimal(transaction.amount_in):
            await asyncio.gather(
                self.log_transaction_message(
                    transaction,
                    (
                        "Expected withdrawal amount_in={} differs from "
                        "received (stellar_transaction_id={}) withdrawal "
                        "amount_in={}".format(
                            transaction.amount_in, horizon_response["id"], amount_received
                        )
                    )
                ),
                self.update_transactions(
                    [transaction],
                    status="error",
                    stellar_transaction_id=horizon_response["id"],
                    paging_token=horizon_response["paging_token"],
                )
            )
        else:
            await asyncio.gather(
                self.log_transaction_message(
                    transaction,
                    "Withdrawal received with correct amount (stellar_transaction_id={})".format(
                        horizon_response["id"]
                    )
                ),
                self.update_transactions(
                    [transaction],
                    status="pending_anchor",
                    from_address=from_address,
                    stellar_transaction_id=horizon_response["id"],
                    paging_token=horizon_response["paging_token"],
                )
            )

    @overrides
    async def update_transactions(
        self, transactions: List[fawaris.Sep24Transaction], **values
    ):
        ids = [transaction.id for transaction in transactions]
        query = (
            tables.sep24_transactions.update()
            .where(tables.sep24_transactions.c.id.in_(ids))
            .values(dict(values))
        )
        coroutines = []
        for transaction in transactions:
            coroutines.append(
                self.log_transaction_message(
                    transaction,
                    f"Updating values: {values}"
                )
            )
        coroutines.append(self.database.execute(query))
        await asyncio.gather(*coroutines)

    @overrides
    async def send_deposit(self, deposit: fawaris.Sep24Transaction) -> None:
        payment_args = dict(
            source_secret=self.distribution_secret,
            horizon_url=self.horizon_url,
            network_passphrase=self.network_passphrase,
            destination_account=deposit.to_address,
            amount=deposit.amount_out,
            asset_code=deposit.asset.code,
            asset_issuer=deposit.asset.issuer,
            memo=deposit.memo,
            memo_type=deposit.memo_type,
        )
        if deposit.claimable_balance_supported:
            account_dict = await fetch_account(self.horizon_url, deposit.to_address)
            if is_pending_trust(account_dict, deposit.asset.code, deposit.asset.issuer):
                results = await asyncio.gather(
                    stellar_create_claimable_balance(
                        source_secret=self.distribution_secret,
                        horizon_url=self.horizon_url,
                        network_passphrase=self.network_passphrase,
                        destination_account=deposit.to_address,
                        amount=deposit.amount_out,
                        asset_code=deposit.asset.code,
                        asset_issuer=deposit.asset.issuer,
                        memo=deposit.memo,
                        memo_type=deposit.memo_type,
                    ),
                    self.log_transaction_message(
                        deposit,
                        "Creating claimable balance"
                    )
                )
                tx = results[0]
                await self.update_transactions(
                    [deposit],
                    status="completed",
                    stellar_transaction_id=tx["transaction_hash"],
                    claimable_balance_id=tx[get_claimable_balance_id(tx)],
                )
                return None

        results = await asyncio.gather(
            stellar_send_payment(**payment_args),
            self.log_transaction_message(
                deposit,
                "Sending stellar payment",
            )
        )
        tx = results[0]
        await self.update_transactions(
            [deposit],
            status="completed",
            stellar_transaction_id=tx["transaction_hash"],
        )
        return None

    @overrides
    async def get_withdraw_anchor_account_cursor(self, account: str) -> Optional[str]:
        query = tables.sep24_transactions.select().\
            where(tables.sep24_transactions.c.kind == "withdrawal").\
            where(tables.sep24_transactions.c.withdraw_anchor_account == account).\
            where(tables.sep24_transactions.c.status == "completed").\
            order_by(tables.sep24_transactions.c.started_at.desc())
        completed_transactions = []
        row = await self.database.fetch_one(query)
        if row:
            return self.row_to_transaction(row).paging_token
        return None

    def row_to_transaction(self, row):
        row = dict(row)
        asset_code = row.pop("asset_code")
        asset_issuer = row.pop("asset_issuer")
        transaction = Sep24Transaction(
            **{
                **row,
                "asset": fawaris.Asset(
                    code=asset_code,
                    issuer=asset_issuer,
                    decimal_places=self.assets[asset_code].decimal_places,
                )
            }
        )
        return transaction

    def transaction_to_values(self, transaction: Sep24Transaction):
        values = {
            "asset_code": transaction.asset.code,
            "asset_issuer": transaction.asset.issuer,
        }
        values.update(transaction.dict())
        return values

    async def log_transaction_message(self, transaction: Sep24Transaction, message: str):
        query = tables.sep24_transaction_logs.insert()
        await self.database.execute(query=query, values={
            "timestamp": datetime.now(timezone.utc),
            "transaction_id": str(transaction.id),
            "message": message,
        })

    #TODO mark below method as abstractmethod

    @overrides
    async def send_withdrawal(self, withdrawal: fawaris.Sep24Transaction) -> None:
        print("sending withdrawal (no-op)")

    @overrides
    async def is_withdrawal_complete(
        self, withdrawal: fawaris.Sep24Transaction
    ) -> bool:
        print("withdrawal not complete (no-op)")
        return False

    @overrides
    async def is_deposit_received(self, deposit: fawaris.Sep24Transaction) -> bool:
        raise NotImplementedError()

    @overrides
    async def http_get_info(
        self, request: fawaris.Sep24InfoRequest
    ) -> fawaris.Sep24InfoResponse:
        return {
            "deposit": {
                "USDC": fawaris.Sep24InfoResponseDeposit(
                    enabled=True,
                ),
            },
            "withdraw": {
                "USDC": fawaris.Sep24InfoResponseWithdraw(
                    enabled=True,
                ),
            },
        }
