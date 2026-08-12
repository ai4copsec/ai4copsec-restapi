from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from typing import Annotated

from ai4copsec.restapi.api.v1.routes import api_router, get_token_payload, TokenPayload
from ai4copsec.sod.types import SODInput, SODOutput
from ai4copsec.sod.base import ShipOilDetection

#from ai4copsec.restapi.db import ClusterDB


sod = ShipOilDetection()

@api_router.get("/technological_brick/sod/description",
        summary="Technological brick: Ship and oil spill detection",
        tags=["technological_brick"],
)
@cache(expire=3600)
async def sod_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of clusters (available at a particular point in time)
    """
    return "The description of the ship and oil spill detection"


@api_router.post("/technological_brick/sod/ship_detection",
        summary="Ship detection",
        tags=["technological_brick"],
)
async def ship_detection(token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
                         input_data: Annotated[SODInput, Body(examples=[
                            sod.create_input_sample().model_dump()
                            ])]
                        ) -> SODOutput:
    """
    Get the list of clusters (available at a particular point in time)
    """
    result = sod.execute(input_data=input_data)
    return result
