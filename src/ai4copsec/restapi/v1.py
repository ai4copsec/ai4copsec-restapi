#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, exception_handlers, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_utils.tasks import repeat_every
from fastapi_pagination import add_pagination

from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import traceback
import gc


from .app_settings import AppSettings
from .api.v1.router import app as api_v1_app
from .utils.api import find_endpoint_by_name
from .utils.api import createFastAPI

#from .db_operations import DBManager

import logging
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Define lifespan of application, as described in:
    https://fastapi.tiangolo.com/advanced/events/#lifespan
    """
    logging.basicConfig(
        format='[{asctime}][{levelname:^8s}] {name}: {message}',
        style='{',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
    )

    logger.setLevel(logging.DEBUG)  # output of exception handlers above
    logger.info("Setting up cache ...")
    FastAPICache.init(
            backend=InMemoryBackend(),
            prefix="fastapi-cache"
    )

    logger.info("Initializing application ...")
    app_settings = AppSettings.initialize(db_schema_version="v1", force=True)

    yield

    logger.info("Shutting down ...")

tags_metadata = [
    {
        "name": "technological_bricks",
        "description": "Technological bricks that are exposed",

    },
    #{
    #    "name": "node",
    #    "description": "Operations that give **node**-specific results",
    #    "externalDocs": {
    #        "description": "test external",
    #        "url": "https://fastapi.tiangolo.com",
    #    },

    #},
    #{
    #    "name": "job",
    #    "description": "Operations that give **job**-specific results",

    #},
]

app = createFastAPI(
        lifespan=lifespan,
        openapi_tags=tags_metadata,
      )

add_pagination(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Can be set to true if we specify origin
    allow_methods=["*"],
    allow_headers=["*"],
)  # This is called before any FastAPI Request (Cross-Origin Resource Sharing), i.e.
# when the JavaScript code in front-end communicates with the backend

# Instrumenting prometheus metrics on /metrics
Instrumentator().instrument(app).expose(app)


# see https://fastapi.tiangolo.com/tutorial/handling-errors/#fastapis-httpexception-vs-starlettes-httpexception
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code not in [404]:
        logger.debug("", exc_info=exc)
    return await exception_handlers.http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.debug("", exc_info=exc)
    return await exception_handlers.request_validation_exception_handler(request, exc)

@app.exception_handler(Exception)
async def runtime_exception_handler(request: Request, exc: Exception):
    logger.warning(exc)
    traceback.print_tb(exc.__traceback__)

    raise HTTPException(status_code=500,
            detail=f"Internal Error: {exc}")

# Serve API. We want the API to take full charge of its prefix, not involve the SPA mount
# at all, hence we use a submount rather than subrouter.
app.mount(path=api_v1_app.root_path, app=api_v1_app, name="api/v1")
