from collections.abc import Awaitable
import datetime as dt
import networkx as nx
import re
import sqlalchemy
from sqlalchemy import (
        distinct,
        Integer,
        func,
        select,
)
import time
from tqdm import tqdm
import logging

from ai4copsec.restapi.utils import utcnow, fromtimestamp
from ai4copsec.restapi.utils.cache import ttl_cache_async

from .db_base import (
    Database,
    DatabaseSettings,  # noqa
    DEFAULT_HISTORY_INTERVAL_IN_S,
    INTERVAL_1DAY, # noqa
    INTERVAL_1WEEK,  # noqa
    INTERVAL_2WEEKS,  # noqa
)

from .db_base import DatabaseSettings # noqa

logger = logging.getLogger(__name__)

class RestapiDB(Database):
    pass
    #TableMetadata = TableMetadata
