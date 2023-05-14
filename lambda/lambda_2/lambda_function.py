import json
import boto3
import uuid
import time
from boto3.dynamodb.conditions import Key, Attr
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

batch = boto3.client('batch')
logs = boto3.client('logs')

logGroupName = '/aws/batch/job'


def getLogs(logStreamName):
    response_logs = logs.get_log_events(
        logGroupName=logGroupName,
        logStreamName=logStreamName,
        startFromHead=False,
        limit=100,
    )
    messages = ''
    for event in (response_logs)['events']:
        messages = messages+'\n'+(str(event['message']))
    return messages
    
headers = {
    "Content-Type": "application/json"
  }


def lambda_handler(event, context):
    routeKey = event['requestContext']['routeKey']

    if routeKey == 'GET /':
        try:
            response_ddb = table.scan()
        except:
            return {
                "code":500,
                "message":"Cannt find the DynamodbDB table.",
            }
            
        if response_ddb['Count'] == 0:
            return {
                "code":200,
                "message":"OK, but no job was deployed.",
            }
        else:
            return {
                "code":200,
                "message":"OK",
                "data":(response_ddb['Items'])
            }        
    
    elif routeKey == 'GET /{id}':
        
        id = event['pathParameters']['id']
        response_ddb = table.get_item(Key={'id': id})
        
        if 'Item' not in response_ddb:
            return {
                "code":404,
                "message":"Wrong id!Please remove the id after url to scan all ids."
            }

        else:
            
            job_status = (response_ddb)['Item']['job_status']
            job_id = response_ddb['Item']['job_id']
            
            if (job_status == "Initializing_SQS" or job_status == "Initializing_Batch"):
                return {
                    "code":200,
                    "message":"Job is " + job_status,
                    "data":response_ddb['Item']
                }           
            
            elif job_status == "FAILED":
                response_batch = batch.describe_jobs(
                    jobs=[
                        job_id,
                    ]
                ) 

                if response_batch['jobs'] == []: # Batch Job autodeleted
                    return {
                        "code":500,
                        "message":'Job is FAILED. Batch log have been deleted',
                    }

                else:

                    statusReason = response_batch['jobs'][0]['statusReason']
                    
                    try:
                        logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                        getLogs(logStreamName)
                    except:
                        return {
                            "code":500,
                            "message":"Job is FAILED. Does not have logs yet",
                        }
                    else:
                        return {
                            "code":500,
                            "message":"Job is FAILED. Please check logs for error",
                            "data":response_ddb['Item'],
                            "logs":logStreamName,
                            # "logs":getLogs(logStreamName),
                        }
                        
            elif job_status == "SUCCEEDED":
                response_batch = batch.describe_jobs(
                    jobs=[
                        job_id,
                    ]
                ) 
                if response_batch['jobs'] == []: # Batch Job autodeleted

                    return {
                        "code":200,
                        "message":'Job is SUCCEEDED,Logs have been deleted',
                        "data":response_ddb['Item']
                    }
                    
                else:
                    statusReason = response_batch['jobs'][0]['statusReason']
                    logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                    return {
                        "code":200,
                        "message":"Job is SUCCEEDED, Please check logs for info",
                        "data":response_ddb['Item'],
                        "logs":logStreamName,
                        # "logs":getLogs(logStreamName),
                    }
            else:
                if job_status == "RUNNING":
                    response_batch = batch.describe_jobs(
                        jobs=[
                            job_id,
                        ]
                    ) 
                    logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                    return {
                        "code":200,
                        "message":"Job is RUNNING, Please check logs for error",
                        "data":response_ddb['Item'],
                        "logs":logStreamName,
                        # "logs":getLogs(logStreamName),
                    }
                    
                else:
                    # status = SUBMITTED/PENDING/RUNNABLE/STARTING/
                    return {
                        "code":200,
                        "message":"Job is "+job_status+",Please wait",
                        "data":response_ddb['Item']
                    }
