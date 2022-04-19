import json
import boto3
import uuid
import time
import ast
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

batch = boto3.client('batch')

sqs = boto3.client('sqs')
queue_url = os.environ['SQS_QUEUE']

s3 = boto3.resource('s3')
bucket_name = os.environ['S3_BUCKET']
bucket = s3.Bucket(bucket_name)
OUTPUT_PREFIX = "output/"
job_Definition_name = os.environ['JOB_DEFINITION_NAME']

# Handle POST & DELETE & CANCEL from SQS


def method_post(payload):
    payload_dict = ast.literal_eval(payload)
    id = payload_dict['id']
    # paramaters for batch
    fasta = payload_dict['fasta']
    file_name = payload_dict['file_name']
    max_template_date = payload_dict['max_template_date']
    model_preset = payload_dict['model_preset']
    db_preset = payload_dict['db_preset']
    num_multimer_predictions_per_model = payload_dict['num_multimer_predictions_per_model']
    run_relax = payload_dict['run_relax']

    que = payload_dict['que']
    gpu = payload_dict['gpu']

    # submit batch job

    if que == 'p4':
        vcpu = 12
        memory = 140000
    else:
        vcpu = 8
        memory = 60000

    response_batch = batch.submit_job(
        jobName=fasta,
        jobQueue=que,
        jobDefinition=job_Definition_name,
        parameters={
            'fasta_paths': file_name,
            'max_template_date': max_template_date,
            'model_preset': model_preset,
            'db_preset': db_preset,
            'num_multimer_predictions_per_model': str(num_multimer_predictions_per_model),
            'run_relax':run_relax,
        },
        propagateTags=False,
        containerOverrides={
            'resourceRequirements': [
                {
                    "type": "MEMORY",
                    "value": str(memory*gpu)
                },
                {
                    "type": "VCPU",
                    "value": str(vcpu*gpu)
                },
                {
                    'value': str(gpu),
                    'type': 'GPU'
                },
            ],
            'environment': [
                {
                    'name': 'id',
                    'value': id
                },
                {
                    'name':'AWS-GCR-HCLS-Solutions',
                    'value':'Alphafold2'
                }
            ],
        },
    )
    print("response_batch from submit_job:"+str(response_batch))

    job_id = response_batch['jobId']

    response_ddb = table.update_item(
        Key={
            'id': id
        },
        UpdateExpression='SET job_id = :job_id,job_status = :job_status',
        ExpressionAttributeValues={
            ':job_id': job_id,
            ':job_status': 'Initializing_BATCH'
        }
    )

    print("response_ddb from update_item"+str(response_ddb))
    
def method_delete(id):
    response_ddb = table.get_item(Key={'id': id})
    job_status = response_ddb['Item']['job_status']

    if job_status == "FAILED":
        print("Failed jobs just delete dynamodb")
        response_ddb = table.delete_item(Key={'id': id})
    elif job_status == "SUCCEEDED":
        s3_foleder_name = (
            response_ddb['Item']['file_name'].split('.'))[0]
        Prefix = OUTPUT_PREFIX+s3_foleder_name
        response_s3 = bucket.objects.filter(Prefix=Prefix).delete()
        print("response_s3:"+str(response_s3))
        response_ddb = table.delete_item(Key={'id': id})
    
    print("response_ddb from delete_item:"+str(response_ddb))

def method_cancel(id):
    response_ddb = table.get_item(Key={'id': id})
    job_id = response_ddb['Item']['job_id']
    job_status = response_ddb['Item']['job_status']
    # Cant cancel a job in Initializing_SQS/Initializing_Batch status.
    if job_status == "STARTING" or job_status == "RUNNING":

        response_batch = batch.terminate_job(
            jobId=job_id,
            reason='Terminated by user via cli'
        )

        print("response_batch from terminate_job:"+str(response_batch))

    elif job_status == "SUBMITTED" or job_status == "PENDING" or job_status == "RUNNABLE":
        response_batch = batch.cancel_job(
            jobId=job_id,
            reason='Canceled by user via cli'
        )
        print("response_batch from cancel_job:"+str(response_batch))


def lambda_handler(event, context):
    print(event)
    for record in event['Records']:
        messageId = record['messageId']
        messageAttributes = record['messageAttributes']
        method = messageAttributes['Atcion']['stringValue']

        payload = record['body']
        print ("payload: ",payload)

        # delete sqs message
        response_sqs_delete = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=record['receiptHandle']
        )
        print("response_sqs_delete:"+str(response_sqs_delete))

        print(method)
        id = payload.strip("{}'")
        print ("id: ",id)
        if method == 'POST':
            method_post(payload)
        elif method == 'DELETE':
            method_delete(id)
        elif method == 'CANCEL':
            method_cancel(id)
