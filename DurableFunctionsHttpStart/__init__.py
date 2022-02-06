# This function an HTTP starter function for Durable Functions.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable activity function (default name is "Hello")
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt
 
import logging

import azure.functions as func
import azure.durable_functions as df


async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    client = df.DurableOrchestrationClient(starter)

    json_input = {"storage_account_name": req.params.get('storage_account_name'), "file_system": req.params.get('file_system'), "number_of_folders": req.params.get('number_of_folders'), "restore_date": req.params.get('restore_date')}

    instance_id = await client.start_new(req.route_params["functionName"], None, json_input)

    logging.info(f"Started orchestration with ID = '{instance_id}'.")

    return client.create_check_status_response(req, instance_id)