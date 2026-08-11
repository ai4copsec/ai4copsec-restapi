from fastapi import Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.db_operations import DBManager
from ai4copsec.restapi.api.v1.routes import api_router, get_token_payload, TokenPayload
from ai4copsec.sod.types import SODInput, SODOutput

#from ai4copsec.restapi.db import ClusterDB



from typing import Annotated

@api_router.get("/technological_brick/sod/",
        summary="Technological brick: Ship and oil spill detection",
        tags=["technological_brick"],
)
@cache(expire=3600)
async def sod_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of clusters (available at a particular point in time)
    """
    return "The description of the ship and oil spill detection"
