# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

# https://docs.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-cloud-backup?tabs=python

import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient
)

def main(jsoninput: str) -> str:

    logging.warning(f"Input data: {str(jsoninput)}")
    storage_account_name = jsoninput["storage_account_name"]
    file_system = jsoninput["file_system"]
    number_of_folders = int(jsoninput["number_of_folders"])
    #
    # In case no MI is used, add AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET to environment variables
    token_credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url="{}://{}.blob.core.windows.net".format("https", storage_account_name), credential=token_credential)
    container_client = blob_service_client.get_container_client(file_system)

    folders = []
    i = 0
    folder_list = container_client.walk_blobs(delimiter='/')
    for folder in folder_list:
        if folder.name != "_log/" and folder.name != "_logexception/":
            folders.append(folder.name)
            i+=1
        if (i >= number_of_folders):
           break

    return folders