from logging import Logger, getLogger
from typing import Annotated

from ai4copsec.tbi.core import ModelRegistry
from ai4copsec.tbi.ais_anomaly_detection.base import AISAnomalyDetection
from ai4copsec.tbi.ais_anomaly_detection.types import Output, Input
from fastapi import Body, Depends
from fastapi_cache.decorator import cache

from ai4copsec.restapi.api.v1.routes import TokenPayload, api_router, get_token_payload
from ai4copsec.restapi.api.v1.tb_common import execute_or_http_error

logger: Logger = getLogger(__name__)

aad = AISAnomalyDetection()

@api_router.get(
    "/technological_brick/aad/description",
    summary="Technological brick: AIS Anomaly Detection",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def aad_description(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the description of the AIS anomaly detection technological brick
    """
    return "The description of the AIS anomaly detection"


@api_router.get(
    "/technological_brick/aad/algorithms",
    summary="List the AIS anomaly detection algorithms available for the 'approach.algorithm' input field",
    tags=["technological_brick"],
)
@cache(expire=3600)
async def aad_algorithms(token_payload: Annotated[TokenPayload, Depends(get_token_payload)]):
    """
    Get the list of registered AAD algorithms, with their metadata (e.g. supported modes)
    """
    return ModelRegistry.list(AISAnomalyDetection.BRICK)


@api_router.post(
    "/technological_brick/aad/compute",
    summary="AIS AISAnomaly Detection",
    tags=["technological_brick"],
)
async def drift_analysis(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    input_data: Annotated[Input, Body(examples=[aad.create_input_sample().model_dump()])],
    ) -> Output:
    """
    Compute a AIS anomaly detection
    """
    return await execute_or_http_error(
        aad.execute,
        logger=logger,
        label="AIS Anomaly Detection",
        input_data=input_data,
    )
