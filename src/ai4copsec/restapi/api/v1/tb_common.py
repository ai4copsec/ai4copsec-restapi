"""Shared helpers for the `/technological_brick/*` routes.

Each technological brick's `execute()` raises `ai4copsec.tbi.core.UnknownAlgorithmError` for
an unrecognized `algorithm`, and (where the brick has a mode concept, e.g. `sod`/`dan`) a
brick-specific `UnsupportedModeError` - both subclass either `LookupError` or `ValueError`
and represent bad request content, not a technological-brick failure.
"""

from collections.abc import Callable
from logging import Logger

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool


async def execute_or_http_error(execute: Callable, /, *, logger: Logger, label: str, **kwargs):
    """Run a technological brick's blocking `execute()` in a worker thread.

    Translates the brick's own validation errors into a 400, and any other failure into a
    500, so the event loop is never blocked by a compute-heavy call.

    Args:
        execute: The bound `execute` method to call, e.g. `sod.execute`.
        logger: Logger of the calling route module.
        label: Human-readable description of the operation, used in error messages.
        **kwargs: Forwarded to `execute` (typically `input_data=...`).

    Returns:
        Whatever `execute` returns.

    Raises:
        HTTPException: 400 for `LookupError`/`ValueError` (unknown algorithm/unsupported
            mode), 500 for anything else.
    """
    try:
        return await run_in_threadpool(execute, **kwargs)
    except (LookupError, ValueError) as e:
        logger.info(f"{label} rejected: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:  # noqa: BLE001 - translate any TB failure into a controlled HTTP error
        logger.error(f"{label} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} failed: {e}",
        )
