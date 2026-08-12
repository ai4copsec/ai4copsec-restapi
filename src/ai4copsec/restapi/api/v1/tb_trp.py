from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from ai4copsec.tbi.trajectory_prediction.base import TrajectoryPrediction
from ai4copsec.tbi.trajectory_prediction.types import Input as TRPInput
from ai4copsec.tbi.trajectory_prediction.types import Output as TRPOutput
from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload
from ai4copsec.restapi.api.v1.tb_common import execute_or_http_error

logger: Logger = getLogger(__name__)

trp = TrajectoryPrediction()


@api_router.get(
    "/technological_brick/trp/description",
    summary="Technological brick: Trajectory prediction",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def trp_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the description of the trajectory prediction technological brick
    """
    return "The description of the trajectory prediction"


@api_router.get(
    "/technological_brick/trp/algorithms",
    summary="List the trajectory prediction algorithms available for the 'algorithm' input field",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def trp_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of registered TRP algorithms, with their metadata
    """
    return ModelRegistry.list(TrajectoryPrediction.BRICK)


@api_router.post(
    "/technological_brick/trp/predict",
    summary="Trajectory prediction",
    tags=["technological_brick"],
)
async def trajectory_prediction(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    input_data: Annotated[TRPInput, Body(examples=[trp.create_input_sample().model_dump()])],
) -> TRPOutput:
    """
    Predict a trajectory for the given historic waypoints/context
    """
    return await execute_or_http_error(
        trp.execute,
        logger=logger,
        label="Trajectory prediction",
        input_data=input_data,
    )
