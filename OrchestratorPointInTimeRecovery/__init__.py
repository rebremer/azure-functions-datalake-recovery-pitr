# This function is not intended to be invoked directly. Instead it will be
# triggered by an HTTP starter function.
# Before running this sample, please:
# - create a Durable activity function (default name is "Hello")
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
import json

import azure.functions as func
import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):


    input_json = context.get_input()
    folders = yield context.call_activity("ActivityGetFolderList", input_json)

    tasks = []
    for folder in folders:
        input_json["folder_name"] = folder
        tasks.append(context.call_activity('ActivityPointInTimeRecovery', input_json))

    results = yield context.task_all(tasks)
    total_bytes = sum(results)
    return total_bytes

main = df.Orchestrator.create(orchestrator_function)