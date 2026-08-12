from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from ai4copsec.tbi.drift_analysis.base import DriftAnalysis
from ai4copsec.tbi.drift_analysis.types import AnalysisOutput, BackcastOutput, ForecastOutput
from ai4copsec.tbi.drift_analysis.types import Input as DANInput
from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload
from ai4copsec.restapi.api.v1.tb_common import execute_or_http_error

logger: Logger = getLogger(__name__)

dan = DriftAnalysis()


@api_router.get(
    "/technological_brick/dan/description",
    summary="Technological brick: Drift analysis",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def dan_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the description of the drift analysis technological brick
    """
    return "The description of the drift analysis"


@api_router.get(
    "/technological_brick/dan/algorithms",
    summary="List the drift analysis algorithms available for the 'approach.algorithm' input field",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def dan_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of registered DAN algorithms, with their metadata (e.g. supported modes)
    """
    return ModelRegistry.list(DriftAnalysis.BRICK)


@api_router.post(
    "/technological_brick/dan/compute",
    summary="Drift analysis (forecast/backcast/analyse, depending on the 'mode' input field)",
    tags=["technological_brick"],
)
async def drift_analysis(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    input_data: Annotated[DANInput, Body(examples=[dan.create_input_sample().model_dump()])],
) -> ForecastOutput | BackcastOutput | AnalysisOutput:
    """
    Compute a drift forecast, backcast or delta-analysis, depending on 'mode'

    Note: the concrete Output type - `ForecastOutput`, `BackcastOutput` or
    `AnalysisOutput` - depends on the request's `mode` field.
    """
    return await execute_or_http_error(
        dan.execute,
        logger=logger,
        label="Drift analysis",
        input_data=input_data,
    )
