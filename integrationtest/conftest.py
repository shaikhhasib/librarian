"""
Fixtures for integration testing of the servers and client.
"""

import pytest
import os
import random
import subprocess
import json
import shutil
import sys

from xprocess import ProcessStarter
from socket import gethostname
from pathlib import Path
from pydantic import BaseModel
from hera_librarian import LibrarianClient  


class Server(BaseModel):
    id: int
    base_path: Path
    staging_directory: Path
    store_directory: Path
    database: Path
    LIBRARIAN_CONFIG_PATH: str
    SQLALCHEMY_DATABASE_URI: str
    PORT: str
    ADD_STORES: str
    process: str | None = None


def server_setup(tmp_path_factory) -> Server:
    """
    Sets up a server.
    """

    librarian_config_path = str(Path("./integrationtest/mock_config.json").resolve())

    server_id_and_port = random.randint(1000, 20000)
    tmp_path = tmp_path_factory.mktemp(f"server_{server_id_and_port}")

    database = tmp_path / f"database_{server_id_and_port}.sqlite"

    # Create the other server settings
    staging_directory = tmp_path / f"staging_{server_id_and_port}"
    staging_directory.mkdir()

    store_directory = tmp_path / f"store_{server_id_and_port}"
    store_directory.mkdir()

    store_config = [{
        "store_name": "test_store",
        "store_type": "local",
        "ingestable": True,
        "store_data": {
            "staging_path": str(staging_directory),
            "store_path": str(store_directory),
        },
        "transfer_manager_data": {
            "local": {
                "available": "true",
                "hostname": gethostname(),
            }
        }
    }]

    add_stores = json.dumps(store_config)

    return Server(
        id=server_id_and_port,
        base_path=tmp_path,
        staging_directory=staging_directory,
        store_directory=store_directory,
        database=database,
        LIBRARIAN_CONFIG_PATH=librarian_config_path,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database}",
        PORT=str(server_id_and_port),
        ADD_STORES=add_stores,
    )


@pytest.fixture(scope="session")
def start_server(xprocess, tmp_path_factory, request):
    """
    Starts a single server with pytest-xprocess.
    """

    setup = server_setup(tmp_path_factory)

    class Starter(ProcessStarter):
        pattern = "Uvicorn running on"
        args = [sys.executable, shutil.which("librarian-server-start")]
        timeout = 10
        env = {
            "LIBRARIAN_CONFIG_PATH": setup.LIBRARIAN_CONFIG_PATH,
            "SQLALCHEMY_DATABASE_URI": setup.SQLALCHEMY_DATABASE_URI,
            "PORT": setup.PORT,
            "ADD_STORES": setup.ADD_STORES,
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", None),
            "ALEMBIC_CONFIG_PATH": str(Path(__file__).parent.parent),
            "ALEMBIC_PATH": shutil.which("alembic")
        }

    xprocess.ensure("server", Starter)

    setup.process = "server"
    yield setup

    if request.session.testsfailed:
        print("Tests failed, data may be available at", xprocess.getinfo("server").logpath)
        print("Tests failed, database may be available at", setup.database)

    xprocess.getinfo("server").terminate()

@pytest.fixture
def librarian_client(start_server) -> LibrarianClient:
    """
    Returns a LibrarianClient connected to the server.
    """

    client = LibrarianClient(
        conn_name="test",
        conn_config={
            "url": f"http://localhost:{start_server.id}/",
            "authenticator": None
        }
    )

    yield client

    del client


@pytest.fixture
def garbage_file(tmp_path) -> Path:
    """
    Returns a file filled with garbage at the path.
    """

    data = random.randbytes(1024)

    path = tmp_path / "garbage_file.txt"

    with open(path, "wb") as handle:
        handle.write(data)

    yield path

    # Delete the file for good measure.
    path.unlink()

