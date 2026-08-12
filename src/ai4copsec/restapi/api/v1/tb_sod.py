from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from ai4copsec.tbi.sod.base import ShipOilDetection
from ai4copsec.tbi.sod.types import SODInput, SODOutput
from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload
from ai4copsec.restapi.api.v1.tb_common import execute_or_http_error

logger: Logger = getLogger(__name__)

sod = ShipOilDetection()


@api_router.get(
    "/technological_brick/sod/description",
    summary="Technological brick: Ship and oil spill detection",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def sod_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of clusters (available at a particular point in time)
    """
    return "The description of the ship and oil spill detection"


@api_router.get(
    "/technological_brick/sod/algorithms",
    summary="List the ship/oil-spill detection algorithms available for the 'algorithm' input field",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def sod_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of registered SOD algorithms, with their metadata (e.g. supported modes)
    """
    return ModelRegistry.list(ShipOilDetection.BRICK)


@api_router.post(
    "/technological_brick/sod/detect",
    summary="Ship detection",
    tags=["technological_brick"],
)
async def oil_or_ship_detection(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    input_data: Annotated[SODInput, Body(examples=[sod.create_input_sample().model_dump()])],
) -> SODOutput:
    """
    Get the list of clusters (available at a particular point in time)
    """
    return await execute_or_http_error(
        sod.execute,
        logger=logger,
        label="Ship/oil-spill detection",
        input_data=input_data,
    )
