import json
import logging
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobClient
)
import azure.functions as func

# https://docs.microsoft.com/en-us/azure/event-grid/resize-images-on-storage-blob-upload-event

def main(event: func.EventGridEvent):

    input = json.dumps({
        'id': event.id,
        'data': event.get_json(),
        'topic': event.topic,
        'subject': event.subject,
        'event_type': event.event_type,
    })

    logging.info('Python EventGrid trigger processed an event: %s', input)
    # In case no MI is used, add AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET to environment variables
    token_credential = DefaultAzureCredential()

    currentTime = datetime.now()
    blob_client = BlobClient.from_blob_url(blob_url=event.get_json()["blobUrl"], credential=token_credential)
    metadata={'time':'{}'.format(currentTime)}
    blob_client.create_snapshot(metadata=metadata)