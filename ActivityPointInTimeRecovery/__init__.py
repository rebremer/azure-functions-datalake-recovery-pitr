# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

# https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-storage-blob-triggered-function

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
    restore_date = jsoninput["restore_date"]
    restore_date_object = parse(restore_date) # string to datetime object

    # In case no MI is used, add AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET to environment variables
    token_credential = DefaultAzureCredential()

    # Create handlers
    blob_service_client = BlobServiceClient(account_url="{}://{}.blob.core.windows.net".format("https", storage_account_name), credential=token_credential)
    container_client = blob_service_client.get_container_client(file_system)

    # Create blob_list that includes deleted files. Subfolders are also included and need to excluded out during filtering.
    # Example of blob_list is as follows:
    # -dir1
    #  -subdir1, deleted=false
    #   -file1, deleted=true
    #   -file2, deleted=false
    #  -dir2, deleted=true
    # ...etc

    i = 0
    sub_folder_list = []
    blob_list = container_client.list_blobs(name_starts_with=folder_name, include=['deleted'])
    for blob in blob_list:
        
        blob_client = blob_service_client.get_blob_client(container=file_system, blob=blob.name)
        
        # undelete file if deleted. Won't change update time stamp of blob
        if blob.deleted == True:
            blob_client.undelete_blob()

        # check if "file" is not a sub folder
        if 'hdi_isfolder' not in blob_client.get_blob_properties()['metadata']:

            # Example of blob_snapshot_list is as follows:
            # file, snapshot=None
            # file, snapshot=date1
            # file, snapshot=date2
            # ...etc
            restore_snapshot = None
            snapshot_last_modified_exists = False
            blob_snapshot_list = container_client.list_blobs(name_starts_with=blob.name, include=['snapshots', 'metadata'])
            for blob_snapshot in blob_snapshot_list:
                if blob_snapshot.snapshot != None:
                    # 1. check if there exists a snapshot of the last modified version of blob
                    if blob_snapshot.last_modified >= blob_client.get_blob_properties()['last_modified']:
                        snapshot_last_modified_exists = True

                    # 2. Determine is snapshot is most recent before restore date
                    if blob_snapshot.last_modified < restore_date_object:
                        # 1a. snapshot is before restore date
                        if restore_snapshot == None:
                            # 1a1. no restore_snapshot yet => current snapshot becomes restore_snapshot candidate
                            restore_snapshot = blob_snapshot
                        elif blob_snapshot.last_modified > restore_snapshot.last_modified:
                            # 1a2. current snapshot is closer to restore date than previous snapshot => current snapshot becomes restore_snapshot candidate
                            restore_snapshot = blob_snapshot

            if snapshot_last_modified_exists == False:
                # Error state, no snapshot exists of last modified blob. When blob is modified, data loss can occur. 
                # Resolve error state by creating snapshot
                metadata={'snapshot_before_restore_date':'{}'.format(restore_date)}
                blob_client.create_snapshot(metadata=metadata)

            print("last_modified: " + str(blob_client.get_blob_properties()['last_modified'] ) + ", restore_date: " + restore_date)

            # Check scenarios
            if blob_client.get_blob_properties()['last_modified'] < restore_date_object:

                # scenario 1: last_modified < restore_date 
                # => no need to restore
                print("Scenario 1: " + str(blob.name) + " last change was before restore date, do nothing")
            elif restore_date_object < blob_client.get_blob_properties()['creation_time']: 
                # scenario 2: restore_date < creation_time 
                # => soft delete file
                print("Scenario 2: " + str(blob.name) + " restore date is before creation time, soft delete")  
                blob_client.delete_blob(delete_snapshots="include")          
            elif restore_snapshot != None:
                # Scenario 3: creation_time < restore_date < last_modified && snapshot before last_modified is found
                # => restore snapshot
                blob_client.start_copy_from_url("{}://{}.blob.core.windows.net/{}/{}?snapshot={}".format("https", storage_account_name, file_system, restore_snapshot.name, restore_snapshot.snapshot))
                metadata={'restored_snapshot':'{}'.format(restore_snapshot.snapshot)}
                blob_client.set_blob_metadata(metadata=metadata)
                print("Scenario 3: Restore snapshot " + str(restore_snapshot.snapshot))
            else:
                # Scenario 4: creation_time < restore_date < last_modified && snapshot before last_modified is NOT found
                # => Error state, no way to resolve, requires analysis of content of blob what shall be done. 
                # => Do nothing, log error message
                blob_client = blob_service_client.get_blob_client(container=file_system, blob="_log/exception/" + restore_date + ".txt")
                blob_client.append_block(data="Scenario 4: " + str(blob.name) + restore_date + "_" + str(datetime.now()),overwrite=True)

                print("Scenario 4: error")
        else:
            print (blob.name + ' is a directory')
            if blob.name + "/" != folder_name:
                sub_folder_list.insert(0, blob)
        #
        i+=1

        blob_client = blob_service_client.get_blob_client(container=file_system, blob="_log/" + folder_name + "restore-correlation" + str(restore_date) + ".txt")
        blob_client.upload_blob(data="correlation_" + restore_date + "_" + str(datetime.now()),overwrite=True)

    # delete empty folders that were created before restore date
    for sub_folder in sub_folder_list:
        if sub_folder.last_modified < restore_date_object:
            # folder was created before restore date, don't do anyting
            print("folder was created before restore date, don't do anyting")
        else:
            sub_folder_blob_list = container_client.list_blobs(name_starts_with=sub_folder.name + "/")
            no_blobs_in_sub_folder = True
            for sub_folder_blob in sub_folder_blob_list:
                sub_folder_blob_client = blob_service_client.get_blob_client(container=file_system, blob=sub_folder_blob.name)
                if 'hdi_isfolder' not in sub_folder_blob_client.get_blob_properties()['metadata']:
                    # subfolder contains blob, don't delete subfolder, break
                    no_blobs_in_sub_folder = False
                    break
                elif sub_folder_blob.last_modified < restore_date_object: 
                    # subfolder contains another subfolder that was created before restore date, don't delete subfolder, break
                    no_blobs_in_sub_folder = False
                    break

            if no_blobs_in_sub_folder == True:
                print (sub_folder)
                sub_folder_blob_client = blob_service_client.get_blob_client(container=file_system, blob=sub_folder.name)
                sub_folder_blob_client.delete_blob()

    return int(i)