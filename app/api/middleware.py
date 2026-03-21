from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.common.constants import RATE_LIMIT_DEFAULT

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])


def setup_middleware(app: FastAPI) -> None:
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://krktransit.pl"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
