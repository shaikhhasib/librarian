"""
Contains endpoints for pinging and requesting a ping back.
"""

from ..webutil import ServerError
from ..database import session, query
from ..logger import log
from ..settings import server_settings

from fastapi import APIRouter

from hera_librarian.models.ping import PingRequest, PingResponse


router = APIRouter(prefix="/api/v2/ping")


@router.post("/", response_model=PingResponse)
def ping(request: PingRequest):
    """
    Pings the librarian server. Returns some information about
    the server.
    """

    log.debug(f"Received ping request: {request}")

    return PingResponse(
        name=server_settings.displayed_site_name,
        description=server_settings.displayed_site_description,
    )
