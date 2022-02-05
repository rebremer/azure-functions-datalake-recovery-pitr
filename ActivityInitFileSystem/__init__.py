# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

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

def main(jsoninput: str) -> str:
    
    logging.warning(f"Input data: {str(jsoninput)}")
    storage_account_name = jsoninput["storage_account_name"]
    file_system = jsoninput["file_system"]
    counter = int(jsoninput["counter"])
    authentication = jsoninput["authentication"]

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
    adls_service_client = DataLakeServiceClient(account_url="{}://{}.dfs.core.windows.net".format("https", storage_account_name), credential=token_credential)
    file_system_client = adls_service_client.get_file_system_client(file_system=file_system)
    #
    blob_service_client = BlobServiceClient(account_url="{}://{}.blob.core.windows.net".format("https", storage_account_name), credential=token_credential)
    #container_client = blob_service_client.get_container_client("test")
    #
    try:
        file_system_client.create_directory("dir" + str(10000 - counter))
    except ResourceExistsError:
        print ("dir" + str(10000 - counter) + " already exists")
        return 0
    #
    i=0
    while (i < 100):
        currentTime = datetime.now()  
        j=0
        while (j < 10):
            blob_client = blob_service_client.get_blob_client(container=file_system, blob="dir" + str(10000 - counter) + "/subdir" + str(i) + "/test-snapshot" + str(j) + ".txt")
            blob_client.upload_blob(data="test-snapshot_" + str(currentTime))
            #
            j+=1
        i+=1
    
    return int(i*j)