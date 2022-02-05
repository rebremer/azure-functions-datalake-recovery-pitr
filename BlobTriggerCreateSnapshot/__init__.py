import logging
import os
from datetime import datetime
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient
)

import azure.functions as func

def main(containerblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {containerblob.name}\n"
                 f"Blob Size: {containerblob.length} bytes")

    container_name = containerblob.name.partition('/')[0]
    blob_name = containerblob.name.partition('/')[2]

    # Create token to authenticate to storage account
    if authentication == "spn":
        # Create token to authenticate to storage account
        token_credential = ClientSecretCredential(
            os.environ["TENANT_ID"],
            os.environ["CLIENT_ID"],
            os.environ["CLIENT_SECRET"]
        )
    else:
        token_credential = DefaultAzureCredential()
    #
    currentTime = datetime.now()
    blob_service_client = BlobServiceClient(account_url="{}://{}.blob.core.windows.net".format("https", STORAGE_ACCOUNT_NAME), credential=token_credential)
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    metadata={'time':'{}'.format(currentTime)}
    snapshot_blob = blob_client.create_snapshot(metadata=metadata)