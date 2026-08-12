from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from ai4copsec.tbi.ship_identification.base import ShipIdentification
from ai4copsec.tbi.ship_identification.types import Input as SHIInput
from ai4copsec.tbi.ship_identification.types import Output as SHIOutput
from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload
from ai4copsec.restapi.api.v1.tb_common import execute_or_http_error

logger: Logger = getLogger(__name__)

shi = ShipIdentification()


@api_router.get(
    "/technological_brick/shi/description",
    summary="Technological brick: Ship identification",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def shi_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the description of the ship identification technological brick
    """
    return "The description of the ship identification"


@api_router.get(
    "/technological_brick/shi/algorithms",
    summary="List the ship identification algorithms available for the 'algorithm' input field",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def shi_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of registered SHI algorithms, with their metadata
    """
    return ModelRegistry.list(ShipIdentification.BRICK)


@api_router.post(
    "/technological_brick/shi/identify",
    summary="Ship identification",
    tags=["technological_brick"],
)
async def ship_identification(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    input_data: Annotated[SHIInput, Body(examples=[shi.create_input_sample().model_dump()])],
) -> SHIOutput:
    """
    Identify vessel candidates matching the given waypoints/vessel characteristics
    """
    return await execute_or_http_error(
        shi.execute,
        logger=logger,
        label="Ship identification",
        input_data=input_data,
    )
