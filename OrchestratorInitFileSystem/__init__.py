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
    number_of_folders = int(input_json.get('number_of_folders'))
    #
    tasks = []
    i = 0
    while (i < number_of_folders):
        print(str(i))
        input_json["counter"] = i
        tasks.append(context.call_activity('ActivityInitFileSystem', input_json))
        i+=1
    
    results = yield context.task_all(tasks)
    total_bytes = sum(results)
    return total_bytes

main = df.Orchestrator.create(orchestrator_function)