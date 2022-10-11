# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
from datetime import datetime
from dateutil.parser import parse
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient
)

def main(jsoninput: str) -> str:

    logging.warning(f"Input data: {str(jsoninput)}")
    storage_account_name = jsoninput["storage_account_name"]
    file_system = jsoninput["file_system"]
    folder_name = jsoninput["folder_name"]

    # In case no MI is used, add AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET to environment variables
    token_credential = DefaultAzureCredential()

    # Create handlers
    blob_service_client = BlobServiceClient(account_url="{}://{}.blob.core.windows.net".format("https", storage_account_name), credential=token_credential)
    container_client = blob_service_client.get_container_client(file_system)

    count=0
    blob_list = container_client.list_blobs(name_starts_with=folder_name)
    num = 0
    size = 0
    for blob in blob_list:

        if blob.size == 0:
            # check if "file" is not a sub folder
            blob_client = blob_service_client.get_blob_client(container=file_system, blob=blob.name)

            if 'hdi_isfolder' not in blob_client.get_blob_properties()['metadata']:
                # Empty file, not a sub folder. Increase file count with 1
                num += 1
        else:
            num += 1
            size += blob.size

    jsonoutput = []
    jsonoutput.append(num)
    jsonoutput.append(size)
    return jsonoutput