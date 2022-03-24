import sqlalchemy

metadata = sqlalchemy.MetaData()

sep24_transactions = sqlalchemy.Table(
    "transactions",
    metadata,

    # extra fields (not part of Sep24Transaction model)
    sqlalchemy.Column("asset_code", sqlalchemy.Text),
    sqlalchemy.Column("asset_issuer", sqlalchemy.Text),

    # 1-to-1 fields to Sep24Transaction model
    sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True),
    sqlalchemy.Column("kind", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.Text),
    sqlalchemy.Column("status_eta", sqlalchemy.Integer),
    sqlalchemy.Column("more_info_url", sqlalchemy.Text),
    sqlalchemy.Column("amount_in", sqlalchemy.Numeric),
    sqlalchemy.Column("amount_in_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_out", sqlalchemy.Numeric),
    sqlalchemy.Column("amount_out_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_fee", sqlalchemy.Numeric),
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

