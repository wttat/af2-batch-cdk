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
        limit=20,
    )
    messages = ''
    for event in (response_logs)['events']:
        messages = messages+'\n'+(str(event['message']))
    return messages

def lambda_handler(event, context):
    # return event
    method = eval(json.dumps(event['requestContext']['http']['method']))
    id = json.dumps(event['requestContext']['http']['path']).strip('"/')

    if method == 'GET':
        if id == '':
            try:
                response_ddb = table.scan()
            except:
                return 'Cannt find the dynamodbDB table, please contact admin.\n'
            
            if response_ddb['Count'] == 0:
                return "No job was deployed.\n"
            else:
                return (response_ddb['Items'])
        else:
            response_ddb = table.get_item(Key={'id': id})
            if 'Item' not in response_ddb:
                return "Wrong id!\nPlease remove the id after url to scan all ids~\n"
            else:
                job_status = (response_ddb)['Item']['job_status']
                job_id = response_ddb['Item']['job_id']

                if (job_status == "Initializing_SQS" or job_status == "Initializing_Batch"):
                    return str(response_ddb['Item'])+"\n\n###\n\nThis job is starting and waiting for sending to Batch\n"
                elif job_status == "FAILED":
                        try:
                            response_batch = batch.describe_jobs(
                                jobs=[
                                    job_id,
                                ]
                            )
                        except:
                            messages = 'Logs have been deleted'
                            return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\n####\n\nRecent logs :'+messages+'\n\n####\n\nPlease check your email for download info.\n'
                        else:
                            statusReason = response_batch['jobs'][0]['statusReason']
                            
                            try:
                                logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                                messages = getLogs(logStreamName)
                            except:
                                print("This failed job does not have logs yet")
                                return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+job_status+'\n\n####\n\nThis failed job does not have logs yet.\n'
                            else:
                                return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+job_status+'\n\n####\n\nstatusReason :'+statusReason+'\n\n####\n\nRecent logs :'+messages+'\n\n####\n\nSomething Wrong!!! Please check full logs on cloudwatch logs\n'
                elif job_status == "SUCCEEDED":
                        try:
                            response_batch = batch.describe_jobs(
                                jobs=[
                                    job_id,
                                ]
                            )
                        except:
                            messages = 'Logs have been deleted'
                            return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\n####\n\nRecent logs :'+messages+'\n\n####\n\nPlease check your email for download info.\n'
                        else:
                            statusReason = response_batch['jobs'][0]['statusReason']
                            logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                            messages = getLogs(logStreamName)
                            return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+job_status+'\n\n####\n\nstatusReason :'+statusReason+'\n\n####\n\nRecent logs :'+messages+'\n\n####\n\nPlease check your email for download info.\n'
                else:# status = SUBMITTED/PENDING/RUNNABLE/STARTING/RUNNING
                        response_batch = batch.describe_jobs(
                            jobs=[
                                job_id,
                            ]
                        )
                        if job_status == "RUNNING":
                            logStreamName = response_batch['jobs'][0]['container']['logStreamName']
                            messages = getLogs(logStreamName)
                            return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+job_status+'\n\n####\n\nRecent logs :'+messages+'\n\n####\n\nFull logs on cloudwatch logs\n'
                        else:
                            return '####\n\njob info : \n\n'+str((response_ddb)['Item'])+'\n\n####\n\njob status :'+job_status+',going to run.'+'\n\n'
        return "please use GET/GET{id}/POST/DELETE{id}\n"
