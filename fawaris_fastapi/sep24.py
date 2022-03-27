import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Callable, Any, Optional, Union, Dict
from fastapi import FastAPI
from pydantic import Field
from databases import Database
from fastapi import Depends, Request
from overrides import overrides
from abc import ABC, abstractmethod
import fawaris

from fawaris_fastapi import tables
from fawaris_fastapi import settings
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

class Sep24Transaction(fawaris.Sep24Transaction):
    asset: fawaris.Asset = Field(..., exclude=True)
    paging_token: Optional[str] = Field(None, exclude=True)
    claimable_balance_supported: Optional[str] = Field(None, exclude=True)
    stellar_transaction_response: Optional[str] = Field(None, exclude=True)

    @staticmethod
    def from_db_row(row, *, assets: Dict[str, fawaris.Asset]):
        row = dict(row)
        asset_code = row.pop("asset_code")
        asset_issuer = row.pop("asset_issuer")
        transaction = Sep24Transaction(
            **{
                **row,
                "asset": assets[asset_code],
            }
        )
        return transaction

    @staticmethod
    def to_db_values(transaction):
        values = {
            "asset_code": transaction.asset.code,
            "asset_issuer": transaction.asset.issuer,
            "paging_token": transaction.paging_token,
            "claimable_balance_supported": transaction.claimable_balance_supported,
            "stellar_transaction_response": transaction.stellar_transaction_response,
        }
        values.update(transaction.dict())
        return values


class Sep24(fawaris.Sep24):
    database: Database
    sep10_jwt_secret: str
    distribution_secret: str
    horizon_url: str
    network_passphrase: str
    assets: Dict[str, fawaris.Asset]
    log: Callable[[str], Any]

    def __init__(
        self,
        database: Database,
        sep10_jwt_secret: str,
        distribution_secret: str,
        horizon_url: str,
        network_passphrase: str,
        assets: Dict[str, fawaris.Asset],
        log: Optional[Callable[[str], Any]] = lambda msg: None,
    ):
        self.database = database
        self.sep10_jwt_secret = sep10_jwt_secret
        self.distribution_secret = distribution_secret
        self.horizon_url = horizon_url
        self.network_passphrase = network_passphrase
        self.assets = assets
        self.log = log

    @classmethod
    def new_instance(cls, database: Database):
        return cls(
            database=database,
            sep10_jwt_secret=settings.JWT_SECRET,
            distribution_secret=settings.DISTRIBUTION_SECRET,
            horizon_url=settings.HORIZON_URL,
            network_passphrase=settings.NETWORK_PASSPHRASE,
            assets={
                "USDC": fawaris.Asset(
                    code="USDC",
                    issuer="GCCGEMWASPXY4HWAJTH2BDYKYMLVOAH4K657IDLM5ZE7DGJJCY5EY53J",
                    decimal_places=7,
                )
            },
        )

    def register_routes(self, app: FastAPI):
        @app.post("/sep24/transactions/deposit/interactive")
        async def http_post_transactions_deposit_interactive(
            request=Depends(authenticate(self.sep10_jwt_secret)),
        ):
            data = await detect_and_get_request_data(request)
            req = validate_request_data(data, fawaris.Sep24DepositPostRequest)
            return await self.http_post_transactions_deposit_interactive(
                req, request.token
            )

        @app.post("/sep24/transactions/withdraw/interactive")
        async def http_post_transactions_withdraw_interactive(
            request=Depends(authenticate(self.sep10_jwt_secret)),
        ):
            data = await detect_and_get_request_data(request)
            req = validate_request_data(data, fawaris.Sep24WithdrawPostRequest)
            return await self.http_post_transactions_withdraw_interactive(
                req, request.token
            )

        @app.get("/sep24/info")
        async def http_get_info(request: Request):
            req = validate_request_data(
                dict(request.query_params), fawaris.Sep24InfoRequest
            )
            return await self.http_get_info(req)

        @app.get("/sep24/transactions")
        async def http_get_transactions(
            request=Depends(authenticate(self.sep10_jwt_secret)),
        ):
            req = validate_request_data(
                dict(request.query_params), fawaris.Sep24TransactionsGetRequest
            )
            return await self.http_get_transactions(req, request.token)

        @app.get("/sep24/transaction")
        async def http_get_transaction(
            request=Depends(authenticate(self.sep10_jwt_secret)),
        ):
            req = validate_request_data(
                dict(request.query_params), fawaris.Sep24TransactionGetRequest
            )
            return await self.http_get_transaction(req, request.token)

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
            query = query.where(
                tables.sep24_transactions.c.asset_code == request.asset_code
            )
        transactions = []
        async for row in self.database.iterate(query):
            transactions.append(Sep24Transaction.from_db_row(row, assets=self.assets))
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
            to_address=request.account,
            amount_out="1234.56",
            external_extra="test",
        )
        values = Sep24Transaction.to_db_values(transaction)
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
            transactions.append(Sep24Transaction.from_db_row(row, assets=self.assets))
        return transactions

    @overrides
    async def get_transaction_asset(
        self, transaction: fawaris.Sep24Transaction
    ) -> fawaris.Asset:
        return transaction.asset

    @overrides
    async def process_withdrawal_received(
        self,
        transaction: fawaris.Sep24Transaction,
        amount_received: str,
        from_address: str,
        horizon_response: Dict,
    ):
        if Decimal(amount_received) != Decimal(transaction.amount_in):
            await self.log_transaction_message(
                transaction,
                (
                    "Expected withdrawal amount_in={} differs from "
                    "received (stellar_transaction_id={}) withdrawal "
                    "amount_in={}".format(
                        transaction.amount_in,
                        horizon_response["id"],
                        amount_received,
                    )
                ),
            )
            await self.update_transactions(
                [transaction],
                status="error",
                stellar_transaction_id=horizon_response["id"],
                paging_token=horizon_response["paging_token"],
            )
        else:
            await self.log_transaction_message(
                transaction,
                "Withdrawal received with correct amount (stellar_transaction_id={})".format(
                    horizon_response["id"]
                ),
            )
            await self.update_transactions(
                [transaction],
                status="pending_anchor",
                from_address=from_address,
                stellar_transaction_id=horizon_response["id"],
                paging_token=horizon_response["paging_token"],
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
                self.log_transaction_message(transaction, f"Updating values: {values}")
            )
        await asyncio.gather(*coroutines)
        await self.database.execute(query)

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
            memo=deposit.deposit_memo,
            memo_type=deposit.deposit_memo_type,
        )
        if deposit.claimable_balance_supported:
            account_dict = await fetch_account(self.horizon_url, deposit.to_address)
            if is_pending_trust(account_dict, deposit.asset.code, deposit.asset.issuer):
                await self.log_transaction_message(deposit, "Creating claimable balance")
                tx = await stellar_create_claimable_balance(
                    source_secret=self.distribution_secret,
                    horizon_url=self.horizon_url,
                    network_passphrase=self.network_passphrase,
                    destination_account=deposit.to_address,
                    amount=deposit.amount_out,
                    asset_code=deposit.asset.code,
                    asset_issuer=deposit.asset.issuer,
                    memo=deposit.deposit_memo,
                    memo_type=deposit.deposit_memo_type,
                )
                await self.update_transactions(
                    [deposit],
                    status="completed",
                    stellar_transaction_id=tx["transaction_hash"],
                    claimable_balance_id=tx[get_claimable_balance_id(tx)],
                )
                return None

        await self.log_transaction_message(
            deposit,
            "Sending stellar payment",
        )
        tx = await stellar_send_payment(**payment_args)
        await self.update_transactions(
            [deposit],
            status="completed",
            stellar_transaction_id=tx["transaction_hash"],
        )
        return None

    @overrides
    async def get_withdraw_anchor_account_cursor(self, account: str) -> Optional[str]:
        query = (
            tables.sep24_transactions.select()
            .where(tables.sep24_transactions.c.kind == "withdrawal")
            .where(tables.sep24_transactions.c.withdraw_anchor_account == account)
            .where(tables.sep24_transactions.c.status == "completed")
            .order_by(tables.sep24_transactions.c.started_at.desc())
        )
        completed_transactions = []
        row = await self.database.fetch_one(query)
        if row:
            return Sep24Transaction.from_db_row(row, assets=self.assets).paging_token
        return None

    async def log_transaction_message(
        self, transaction: Sep24Transaction, message: str
    ):
        query = tables.sep24_transaction_logs.insert()
        await self.database.execute(
            query=query,
            values={
                "timestamp": datetime.now(timezone.utc),
                "transaction_id": str(transaction.id),
                "message": message,
            },
        )

    # TODO mark below method as abstractmethod

    @overrides
    async def send_withdrawal(self, withdrawal: fawaris.Sep24Transaction) -> None:
        print("sending withdrawal to user")

    @overrides
    async def is_withdrawal_complete(
        self, withdrawal: fawaris.Sep24Transaction
    ) -> bool:
        print("withdrawal not complete")
        return False

    @overrides
    async def is_deposit_received(self, deposit: fawaris.Sep24Transaction) -> bool:
        print("deposit received")
        return True

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

