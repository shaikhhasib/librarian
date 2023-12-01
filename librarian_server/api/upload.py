"""
Contains API endpoints for uploading data to the Librarian and its
stores.
"""

from .. import app, db
from ..webutil import ServerError, json_api, required_arg, optional_arg
from ..orm.storemetadata import StoreMetadata, MetaMode
from ..orm.transfer import TransferStatus, IncomingTransfer
from ..file import DeletionPolicy

from .util import pydantic_api

from hera_librarian.models.uploads import (
    UploadInitiationRequest,
    UploadInitiationResponse,
    UploadCompletionRequest,
)
from hera_librarian.models.stores import StoreRequest

from pathlib import Path
from typing import Optional
import datetime


@app.route("/api/v2/upload/stores", methods=["POST", "GET"], endpoint="stores_endpoint")
@pydantic_api
def view_stores(request=None):
    """
    Probes the stores for their metadata and returns it.
    """

    return StoreRequest(stores=[store for store in StoreMetadata.query.all()])


@app.route("/api/v2/upload/stage", methods=["POST", "GET"], endpoint="stage_endpoint")
@pydantic_api(recieve_model=UploadInitiationRequest)
def stage(request: UploadInitiationRequest):
    """
    Initiates an upload to a store.

    Stages a file, and returns information about the transfer
    providers that can be used by the client to upload the file.
    """

    # Figure out which store to use.
    if request.upload_size < 0:
        raise ServerError("Upload size must be positive.")

    # Now we can write to the database.
    transfer = IncomingTransfer.new_transfer(
        uploader=request.uploader, transfer_size=request.upload_size
    )

    db.session.add(transfer)
    db.session.commit()

    # TODO: Original code had known_staging_store stuff here.

    use_store: Optional[StoreMetadata] = None

    for store in StoreMetadata.query.all():
        if not store.store_manager.available:
            continue

        if store.store_manager.free_space > request.upload_size:
            use_store = store
            break

    if use_store is None:
        raise ServerError("No stores available.")

    # Now generate the response; tell client to use this store, and keep a record.

    # Stage the file
    file_name, file_location = use_store.store_manager.stage(
        file_size=request.upload_size, file_name=request.upload_name
    )

    transfer.store_id = use_store.id
    transfer.staging_path = file_name

    db.session.commit()

    response = UploadInitiationResponse(
        available_bytes_on_store=use_store.store_manager.free_space,
        store_name=use_store.name,
        staging_name=file_name,
        staging_location=file_location,
        upload_name=request.upload_name,
        destination_location=request.destination_location,
        transfer_providers=use_store.transfer_managers,
    )

    return response


@app.route("/api/v2/upload/commit", methods=["POST", "GET"], endpoint="commit_endpoint")
@pydantic_api(recieve_model=UploadCompletionRequest)
def commit(request: UploadCompletionRequest):
    """
    Commits a file to a store, called once it has been uploaded.
    """

    store: StoreMetadata = StoreMetadata.from_name(request.store_name)

    # Go grab the transfer from the database.
    transfer = IncomingTransfer.query.filter_by(id=request.transfer_id).first()
    transfer.status = TransferStatus.STAGED
    transfer.transfer_manager_name = request.transfer_manager_name
    transfer.store_path = request.destination_location

    db.session.commit()

    # TODO: Could potentially check that they haven't messed with the tranfser data here.

    store.process_staged_file(
        staged_path=request.staging_location,
        store_path=request.destination_location,
        meta_mode=MetaMode.from_str(request.meta_mode),
        deletion_policy=DeletionPolicy.parse_safe(request.deletion_policy),
        source_name=request.uploader,
        null_obsid=request.null_obsid,
    )

    # Now that the file has been processed, we can unstage the file.
    store.store_manager.unstage(request.staging_name)

    # Clean up the database!
    transfer.status = TransferStatus.COMPLETED
    transfer.end_time = datetime.datetime.now()

    db.session.commit()

    return {"success": True}
