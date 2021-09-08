import json
import boto3
import uuid
import time
import linecache
import os
from botocore.exceptions import ClientError

line_number = 2

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

s3 = boto3.client('s3')
bucket = os.environ['S3_BUCKET']
prefix = 'input/'

sqs = boto3.client('sqs')
queue_url = os.environ['SQS_QUEUE']

def lambda_handler(event, context):
    # return event
    method = eval(json.dumps(event['requestContext']['http']['method']))

    if method == 'POST':
        data = json.loads(event['body'])
        
        # check for file 
        try:
            data['file_name']
        except:
            return 'You need to specific the fasta file name.\n'
        
        file_name = data['file_name']
        key = prefix+file_name
        
        # check file path
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            return ('The fatsa file path is not correct, please put it in s3://'+bucket+'/'+prefix+'\n')
        print ('fasta found')
        
        # get fasta seq
        s3.download_file(bucket,key, '/tmp/'+file_name)
        fasta_seq = linecache.getline('/tmp/'+file_name, line_number).strip()
    
        id = str(uuid.uuid4())
        now = time.asctime()
        
        # decouple Item for both SQS and dynamoDB usage
        
        try:
            data['fasta']
            data['que']
        except:
            return 'You need to at least specific the fasta and que parameters.\n'
        
        max_template_date = ''
        try:
            data['max_template_date']
        except:
            print ('no max_template_date,using dafault max_template_date 2020-05-14')
            max_template_date = '2020-05-14'
        else:
            max_template_date: data['max_template_date']
        
        model_names = ''
        try:
            data['model_names']
        except:
            print ('no model_names,using dafault model_names 1-5')
            model_names = 'model_1,model_2,model_3,model_4,model_5'
        else:
            model_names: data['model_names']
        
        preset = ''
        try:
            data['preset']
        except:
            print ('no preset,using dafault preset full')
            preset = 'full'
        else:
            preset: data['preset']
        
        comment = ''
        try:
            data['comment']
        except:
            print ('no comment')
        else:
            preset: data['preset']
            
        Item={
            'id' : id,
            'fasta' : data['fasta'],
            'fasta_seq':fasta_seq,
            'file_name': file_name,
            'job_id':'none',
            'job_status': 'starting',
            'model_names' : model_names,
            'preset': preset,
            'max_template_date': max_template_date,
            'que': data['que'],
            'time': now,
            'comment': comment
        }
        
        # return Item

        response_ddb= table.put_item(Item=Item)
        print (response_ddb)
        
        response_sqs = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=str(Item),
            DelaySeconds=10,
            MessageAttributes={
                'Atcion': {
                    'StringValue': 'POST',
                    'DataType': 'String'
                }
            },
        )
        
        print (response_sqs)
        if response_sqs['ResponseMetadata']['HTTPStatusCode'] == 200:
            return('\nSuccessful submit Batch job for fasta:' + data['fasta']+ ', id:'+ id+'\n\n'+'Please use $(curl $auth-info $api-gateway-url/'+id+') to query this job'+'\n')
        
    elif method == 'DELETE' or method == 'CANCEL':
        
        id =  json.dumps(event['requestContext']['http']['path']).strip('"/')
        if id == '': 
            return("please specific id for delete or cancel\n")
        else:
            response_ddb = table.get_item(Key={'id':id})
            if 'Item' not in response_ddb:
                return "no such job id to terminate\n"
            else:
                # response_ddb = table.delete_item(Key={'id': id})
                
                status = (response_ddb)['Item']['job_status']
                
                if status == 'allset' and method == 'CANCEL':
                    return "This job has completed, you could use delete method to delete all files"
                
                if status == 'failed' and method == 'CANCEL':
                    return "This job has failed, you could use delete method to delete all files"
                    
                if (status == 'starting' or status == 'running') and method == 'DELETE':
                    return ("You can't DELETE a "+status+" job, please use CANCEL method.\n")
                
                response_sqs = sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=id,
                    DelaySeconds=10,
                    MessageAttributes={
                        'Atcion': {
                            'StringValue': method,
                            'DataType': 'String'
                        }
                    },
                )
                print (response_sqs)
                if response_sqs['ResponseMetadata']['HTTPStatusCode'] == 200:
                    return('Success send '+method+' command to Batch job ,id :' + id+' \n####\nPlease wait 2min and try again.\n')
                # return response_sqs
    
    else:
        return ('Unknown method, Please use POST / DELETE / CANCEL instead.\n')
        
    