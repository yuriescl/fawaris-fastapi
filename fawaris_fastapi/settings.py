from typing import List
from stellar_sdk import Network


DATABASE_URL: str = 'sqlite:///db.sqlite3'
ASYNC_DATABASE_URL: str = 'sqlite+aiosqlite:///db.sqlite3'

JWT_SECRET: str = "@)wqgb)3&e6k&(l8hfm(3wt8=*_x$w@vc$4)&nbih-&2eg9dlh"
SIGNING_SECRET: str = "SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY"
DISTRIBUTION_SECRET: str = "SC5N4HUKY55KO6IETCP4TNJPS4WXCQFRLDCQY5PPAMKZP24BXKMF4ZEU"

HOST_URL: str = "http://localhost"
HOME_DOMAINS: List[str] = ["localhost"]
HORIZON_URL: str = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE: str = Network.TESTNET_NETWORK_PASSPHRASE
