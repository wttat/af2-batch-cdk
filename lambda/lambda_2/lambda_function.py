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
    # logStreamName =  response_batch['jobs'][0]['container']['logStreamName']
    response_logs = logs.get_log_events(
        logGroupName=logGroupName,
        logStreamName=logStreamName,
        startFromHead=False,
        limit=20,
    )
    messages=''
    for event in (response_logs)['events']:
        messages = messages+'\n'+(str(event['message']))
    return messages

## Handle all GET

def lambda_handler(event, context):
    # return event
    method = eval(json.dumps(event['requestContext']['http']['method']))
    id =  json.dumps(event['requestContext']['http']['path']).strip('"/')

    if method == 'GET':
        if id == '': 
            response_ddb = table.scan()
            if response_ddb['Count'] == 0:
                return "no job deployed\n"
            else:
                # return str(response_ddb['Items'])+"\n\n###\n\nPlease add a specfic id after the URL to query the detail\n"
                return (response_ddb['Items'])
        else:
            response_ddb = table.get_item(Key={'id':id})
            if 'Item' not in response_ddb:
                return "Wrong id!\nPlease remove the id after url to scan all ids~\n"
            else:
                status = (response_ddb)['Item']['job_status']
                job_id = response_ddb['Item']['job_id']
                response_batch = batch.describe_jobs(
                    jobs=[
                        job_id,
                    ]
                )
                batch_status = response_batch['jobs'][0]['status']
                if  status == "starting":
                    return str(response_ddb['Item'])+"\n\n###\n\nThis job is starting and waiting for send to Batch\n"
                elif status == "running":
                    # return response_batch
                    
                    if batch_status == "SUBMITTED":
                        return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+'\n\n'
                    elif batch_status == "PENDING":
                        return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+'\n\n'
                    elif batch_status == "RUNNABLE":
                        return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+',if you stuck in this status for a long time, please check your GPU ec2 instances limit'+'\n\n'
                    elif batch_status == "STARTING":
                        return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+',going to run'
                    elif batch_status == "RUNNING":
                        logStreamName =  response_batch['jobs'][0]['container']['logStreamName']
                        messages = getLogs(logStreamName)
                        return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+'\n\n####\n\nLast 20 logs :'+messages+'\n\n####\n\nFull logs on cloudwatch logs\n'
                    else:
                        return "status error,please connact for support"
                elif status == "allset" :
                    statusReason = response_batch['jobs'][0]['statusReason']
                    logStreamName =  response_batch['jobs'][0]['container']['logStreamName']
                    messages = getLogs(logStreamName)
                    return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+'\n\n####\n\nstatusReason :'+statusReason+'\n\n####\n\nLast 20 logs :'+messages+'\n\n####\n\nPlease check your email for download info.\n'
                elif status == "failed":
                    statusReason = response_batch['jobs'][0]['statusReason']
                    logStreamName =  response_batch['jobs'][0]['container']['logStreamName']
                    messages = getLogs(logStreamName)
                    return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+batch_status+'\n\n####\n\nstatusReason :'+statusReason+'\n\n####\n\nLast 20 logs :'+messages+'\n\n####\n\nMaybe Wrong!!! Please check full logs on cloudwatch logs\n'
                else:
                    return 'something wrong'
    else:
        return "please use GET/GET{id}/POST/DELETE{id}\n"
    