import sqlalchemy
from sqlalchemy.dialects import sqlite

metadata = sqlalchemy.MetaData()

sep24_transactions = sqlalchemy.Table(
    "sep24_transactions",
    metadata,

    # extra fields, specific to this implementation
    sqlalchemy.Column("asset_code", sqlalchemy.Text),
    sqlalchemy.Column("asset_issuer", sqlalchemy.Text),
    sqlalchemy.Column("paging_token", sqlalchemy.Text),
    sqlalchemy.Column("claimable_balance_supported", sqlalchemy.Boolean),
    sqlalchemy.Column("stellar_transaction_response", sqlalchemy.JSON),

    # fields 1-to-1 to fawaris.Sep24Transaction
    sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True),
    sqlalchemy.Column("kind", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.Text),
    sqlalchemy.Column("status_eta", sqlalchemy.Integer),
    sqlalchemy.Column("more_info_url", sqlalchemy.Text),
    sqlalchemy.Column("amount_in", sqlalchemy.Text),
    sqlalchemy.Column("amount_in_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_out", sqlalchemy.Text),
    sqlalchemy.Column("amount_out_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_fee", sqlalchemy.Text),
    sqlalchemy.Column("amount_fee_asset", sqlalchemy.Text),
    sqlalchemy.Column("from_address", sqlalchemy.Text),
    sqlalchemy.Column("to_address", sqlalchemy.Text),
    sqlalchemy.Column("external_extra", sqlalchemy.Text),
    sqlalchemy.Column("external_extra_text", sqlalchemy.Text),
    sqlalchemy.Column("deposit_memo", sqlalchemy.Text),
    sqlalchemy.Column("deposit_memo_type", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_anchor_account", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_memo", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_memo_type", sqlalchemy.Text),
    sqlalchemy.Column("started_at", sqlalchemy.DateTime),
    sqlalchemy.Column("completed_at", sqlalchemy.DateTime),
    sqlalchemy.Column("stellar_transaction_id", sqlalchemy.Text),
    sqlalchemy.Column("external_transaction_id", sqlalchemy.Text),
    sqlalchemy.Column("message", sqlalchemy.Text),
    sqlalchemy.Column("refunds", sqlalchemy.JSON),
    sqlalchemy.Column("required_info_message", sqlalchemy.Text),
    sqlalchemy.Column("required_info_updates", sqlalchemy.JSON),
    sqlalchemy.Column("claimable_balance_id", sqlalchemy.Text),
)

sep24_transaction_logs = sqlalchemy.Table(
    "sep24_transaction_logs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime),
    sqlalchemy.Column("transaction_id", sqlalchemy.Text),
    sqlalchemy.Column("message", sqlalchemy.Text),
)
