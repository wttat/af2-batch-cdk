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
job_Definition_name = os.environ['JOB_DEFINITION_NAME']

# Handle POST & DELETE & CANCEL from SQS


def lambda_handler(event, context):
    print(event)
    for record in event['Records']:
        messageId = record['messageId']
        messageAttributes = record['messageAttributes']
        method = messageAttributes['Atcion']['stringValue']

        payload = record['body']

        # delete sqs message
        response_sqs_delete = sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=record['receiptHandle']
        )
        print("response_sqs_delete:"+str(response_sqs_delete))

        print(method)
        if method == 'POST':
            payload_dict = ast.literal_eval(payload)
            id = payload_dict['id']
            # paramaters for batch
            fasta = payload_dict['fasta']
            file_name = payload_dict['file_name']
            model_names = payload_dict['model_names']
            preset = payload_dict['preset']
            max_template_date = payload_dict['max_template_date']
            que = payload_dict['que']
            gpu = payload_dict['gpu']

            # submit batch job

            if que == 'p4':
                vcpu = 12
                memory = 1100000
            else:
                vcpu = 8
                memory = 60000

            response_batch = batch.submit_job(
                jobName=fasta,
                jobQueue=que,
                jobDefinition=job_Definition_name,
                parameters={
                    'fasta_paths': file_name,
                    'preset': preset,
                    'model_names': model_names,
                    'max_template_date': max_template_date
                },
                propagateTags=False,
                containerOverrides={
                    # 'vcpus': vcpu*gpu,
                    # 'memory': memory*gpu,
                    'resourceRequirements': [
                        {
                            "type": "MEMORY",
                            "value": memory*gpu
                        },
                        {
                            "type": "VCPU",
                            "value": vcpu*gpu
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
                    ],
                },
            )
            print("response_batch from submit_job:"+str(response_batch))

            job_id = response_batch['jobId']

            # update dynamodb
            response_ddb = table.update_item(
                Key={
                    'id': id
                },
                UpdateExpression='SET job_id = :job_id,job_status = :job_status',
                ExpressionAttributeValues={
                    ':job_id': job_id,
                    ':job_status': 'running'
                }
                # ReturnValues: "UPDATED_NEW"
            )

            print("response_ddb from update_item"+str(response_ddb))

        elif method == 'DELETE' or method == 'CANCEL':

            id = payload.strip("{}'")

            response_ddb = table.get_item(Key={'id': id})
            job_status = response_ddb['Item']['job_status']

            if method == 'DELETE':
                if job_status == "failed":
                    print("failed jobs just delete dynamodb")
                    response_ddb = table.delete_item(Key={'id': id})
                elif job_status == "allset":
                    # finished job just delete s3 folder
                    s3_foleder_name = (
                        response_ddb['Item']['file_name'].split('.'))[0]
                    Prefix = "output/"+s3_foleder_name+"/"
                    response_s3 = bucket.objects.filter(Prefix=Prefix).delete()
                    print("response_s3:"+str(response_s3))
                    response_ddb = table.delete_item(Key={'id': id})

            elif method == 'CANCEL':  # job_status == "running/starting":
                job_id = response_ddb['Item']['job_id']

                response_batch = batch.describe_jobs(
                    jobs=[
                        job_id,
                    ]
                )
                # return response_batch
                print("response_batch from describe_jobs:"+str(response_batch))
                batch_status = response_batch['jobs'][0]['status']
                if batch_status == "STARTING" or batch_status == "RUNNING":

                    response_batch = batch.terminate_job(
                        jobId=job_id,
                        reason='Terminated by user via cli'
                    )

                    print("response_batch from terminate_job:"+str(response_batch))

                elif batch_status == "SUBMITTED" or batch_status == "PENDING" or batch_status == "RUNNABLE":
                    # something wrong with RUNNABLE
                    response_batch = batch.cancel_job(
                        jobId=job_id,
                        reason='Canceled by user via cli'
                    )
                    print("response_batch from cancel_job:"+str(response_batch))

            # only DELETE method delete ddb

            print("response_ddb from delete_item:"+str(response_ddb))
