"""FastAPI application factory for the FIM Agent web layer.

Usage::

    from fim_agent.web import create_app

    app = create_app()
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure a :class:`FastAPI` application.

    The returned app includes:

    * CORS middleware allowing ``localhost:3000`` (Next.js dev server) and all
      origins (``*``) so that production front-ends work out of the box.
    * The ``/api/react`` and ``/api/dag`` SSE chat endpoints from
      :mod:`fim_agent.web.api.chat`.

    Returns
    -------
    FastAPI
        A fully-configured FastAPI instance ready to be served by Uvicorn.
    """
    app = FastAPI(title="FIM Agent API")

    # -- CORS ---------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Routers ------------------------------------------------------------
    app.include_router(chat_router)

    logger.info("FIM Agent API application created")
    return app
