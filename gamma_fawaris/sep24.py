import uuid
from typing import List, Callable, Any, Optional, Union, Dict
from databases import Database
from fastapi import Depends, Request
from overrides import overrides
from abc import ABC, abstractmethod
import fawaris

from gamma_fawaris import tables
from gamma_fawaris.utils import authenticate, detect_and_get_request_data


def register_routes(app, sep24_obj: fawaris.Sep24):
    @app.post("/sep24/transactions/deposit/interactive")
    async def http_post_transactions_deposit_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        return await sep24_obj.http_post_transactions_deposit_interactive(
            fawaris.Sep24DepositPostRequest(**data), request.token
        )

    @app.post("/sep24/transactions/withdraw/interactive")
    async def http_post_transactions_withdraw_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        return await sep24_obj.http_post_transactions_withdraw_interactive(
            fawaris.Sep24WithdrawPostRequest(**data), request.token
        )

    @app.get("/sep24/info")
    async def http_get_info(request: Request):
        return await sep24_obj.http_get_info(
            fawaris.Sep24InfoRequest(**dict(request.query_params)),
        )

    @app.get("/sep24/transactions")
    async def http_get_transactions(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        return await sep24_obj.http_get_transactions(
            fawaris.Sep24TransactionsGetRequest(**dict(request.query_params)),
            request.token,
        )

    @app.get("/sep24/transaction")
    async def http_get_transaction(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        return await sep24_obj.http_get_transaction(
            fawaris.Sep24TransactionGetRequest(**dict(request.query_params)),
            request.token,
        )


class Sep24Transaction(fawaris.Sep24Transaction):
    asset: fawaris.Asset


class Sep24(fawaris.Sep24):
    sep10_jwt_key: str
    database: Database
    log: Callable[[str], Any]
    asset_issuers: Dict[str, str]

    def __init__(
        self,
        sep10_jwt_key: str,
        database: Database,
        asset_issuers: Dict[str, str],
        log: Optional[Callable[[str], Any]] = lambda msg: None,
    ):
        self.sep10_jwt_key = sep10_jwt_key
        self.database = database
        self.asset_issuers = asset_issuers
        self.log = log

    async def http_post_transactions_deposit_interactive(
        self, request: fawaris.Sep24DepositPostRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24PostResponse:
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return fawaris.Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def http_post_transactions_withdraw_interactive(
        self, request: fawaris.Sep24WithdrawPostRequest, token: fawaris.Sep10Token
    ) -> fawaris.Sep24PostResponse:
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return fawaris.Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    @overrides
    async def http_get_info(
        self, request: fawaris.Sep24InfoRequest
    ) -> fawaris.Sep24InfoResponse:
        return {}

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
    ) -> None:
        if isinstance(request, fawaris.Sep24DepositPostRequest):
            kind = "deposit"
        if isinstance(request, fawaris.Sep24WithdrawPostRequest):
            kind = "withdrawal"
        query = tables.sep24_transactions.insert()
        transaction = Sep24Transaction(
            id=str(uuid.uuid4()),  # TODO make sure it's unique
            kind=kind,
            status="pending_user_transfer_start",
            asset=fawaris.Asset(
                code=request.asset_code, issuer=self.asset_issuers[request.asset_code]
            ),
        )
        values = transaction.dict()
        values["asset_code"] = transaction.asset.code
        values["asset_issuer"] = transaction.asset.issuer
        values.pop("asset")
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
                tables.sep24_transactions.withdraw_anchor_account
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
    async def is_deposit_received(self, deposit: fawaris.Sep24Transaction) -> bool:
        raise NotImplementedError()

    @overrides
    async def is_withdrawal_complete(
        self, withdrawal: fawaris.Sep24Transaction
    ) -> bool:
        raise NotImplementedError()

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
        await self.database.execute(query)

    @overrides
    async def send_withdrawal(self, withdrawal: fawaris.Sep24Transaction) -> None:
        raise NotImplementedError()

    @overrides
    async def send_deposit(self, deposit: fawaris.Sep24Transaction) -> None:
        raise NotImplementedError()

    @overrides
    async def get_withdraw_anchor_account_cursor(self, account: str) -> Optional[str]:
        raise NotImplementedError()

    def row_to_transaction(self, row):
        row = dict(row)
        asset_code = row.pop("asset_code")
        asset_issuer = row.pop("asset_issuer")
        transaction = Sep24Transaction(
            **{**row, "asset": fawaris.Asset(code=asset_code, issuer=asset_issuer)}
        )
        return transaction
