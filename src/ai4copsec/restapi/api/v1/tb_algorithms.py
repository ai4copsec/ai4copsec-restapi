from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from fastapi import Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload

logger: Logger = getLogger(__name__)


@api_router.get(
    "/technological_brick/algorithms",
    summary="List the algorithms registered across all technological bricks",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def all_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get every registered algorithm, grouped by technological brick, with their metadata
    (e.g. supported modes). Equivalent to calling each brick's own `/algorithms` endpoint
    and merging the results by brick.
    """
    return ModelRegistry.list_all()
