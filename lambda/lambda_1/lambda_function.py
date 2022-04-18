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


def submit_sqs(Item,method):
    messages = ''
    response_sqs = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=str(Item),
        DelaySeconds=10,
        MessageAttributes={
            'Atcion': {
                'StringValue': method,
                'DataType': 'String'
            }
        },
    )

    print('submit to sqs',response_sqs)
    
    if response_sqs['ResponseMetadata']['HTTPStatusCode'] == 200:
        if method == 'POST':
            messages = messages + '\nSuccessful submit Batch job for fasta:' + \
                Item['fasta'] + ', id:' + Item['id']+'\n\n' + \
                'Please use $(curl $auth-info $api-gateway-url/' + \
                Item['id']+') to query this job'+'\n\n'
        else:
            messages = messages + 'Successfully send ' + \
            method+' command to Batch job.\n\n'  + '####\nPlease wait 2min and try to query this job again.\n\n'
    else:
        messages = 'SQS submit failed. Please contact admin.'
    return messages

def check_body(event):
    Items = []
    
    # check body format.
    try:
        datas = json.loads(event['body'])
    except:
        raise Exception('Please check HTTP body.It should in json.\n')

    for data in datas:
        
        # generate id
        id = str(uuid.uuid4())
        # generate time
        timestamp = time.asctime()
        
        # check mandatory paramaters
        try:
            fasta = data['fasta']
            que = data['que']
            file_name = data['file_name']
            model_preset = data['model_preset']
        except:
            raise Exception('You need to at least specific the fasta/que/file_name/model_preset parameters.\n')
        
        # check if fasta file exist in s3   
        key = prefix+file_name
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except:
            raise Exception('The fatsa file path is not correct, please put it in s3://'+bucket+'/'+prefix+'\n')
        
        print('fasta found')
        
        # check if que meet the requirements
        # TODO check p4 auto
        if que != 'high' and que != 'mid' and que != 'low' and que != 'p4':
            raise Exception('The job queue should be high or mid or low or p4(depends on region) .\n')

        # check max_template_date
        try:
            max_template_date = data['max_template_date']
        except:
            print('no max_template_date,using dafault max_template_date 2021-11-01')
            max_template_date = '2021-11-01'
        print('max_template_date: ',max_template_date)

        # check if model_preset meet the requirements
        if data['model_preset'] != 'monomer' and data['model_preset'] != 'monomer_casp14' and data['model_preset'] != 'monomer_ptm' and data['model_preset'] != 'multimer':
            raise Exception('The model preset shoudl be monomer or monomer_casp14 or monomer_ptm or multimer')
        print('model_preset: ',model_preset)

        # get fasta seq
        if model_preset != 'multimer':
            s3.download_file(bucket, key, '/tmp/'+file_name)
            fasta_seq = linecache.getline(
                '/tmp/'+file_name, line_number).strip()
        else:
            fasta_seq = "This is a multimer seq"
        
        # check if db_preset meet the requirements
        try:
            db_preset = data['db_preset']
        except:
            print('no preset,using dafault preset full')
            db_preset = 'full_dbs'
        else:
            if db_preset != 'full_dbs' and db_preset != 'reduced_dbs':
                raise Exception('The db preset shoudl be full_dbs or reduced_dbs')
        print('db_preset: ',db_preset)

        # check num_multimer_predictions_per_model
        try:
            num_multimer_predictions_per_model = data['num_multimer_predictions_per_model']
        except:
            print('no num_multimer_predictions_per_model,use default num_multimer_predictions_per_model=5')
            num_multimer_predictions_per_model = 5
        else:
            if str(num_multimer_predictions_per_model).isdigit() == False:
                raise Exception('The num_multimer_predictions_per_model should be a number.\n')

        print('num_multimer_predictions_per_model: ',num_multimer_predictions_per_model)

        # check run_relax
        try:
            run_relax = data['run_relax']
        except:
            print('no run_relax,using dafault preset true')
            run_relax = 'true'
        else:
            if data['run_relax'] != 'true' and data['run_relax'] != 'false':
                raise Exception('The run_relax shoudl be true or false')
        print('run_relax: ',run_relax)
        
        # check comment
        try:
            comment = data['comment']
        except:
            print('no comment')
        print('comment: ',comment)
        
        # check gpu
        try:
            gpu = data['gpu']
        except:
            print('no gpu,use default gpu=1')
            gpu = 1
        else:
            if str(data['gpu']).isdigit() == False:
                raise Exception('The gpu should be a number.\n')
        print('gpu: ',gpu)
        
        if gpu > 1:
            if data['que'] == 'low':
                raise Exception('this que only support 1 GPU')
            if gpu > 4:
                if data['que'] == 'mid':
                    raise Exception('only p3.8xlarge or p4 support more than 4 GPU')
                if gpu > 8:
                    raise Exception('max GPU = 8')
        
        # generate all parameters 
        Item = {
            'id': id,
            'fasta': data['fasta'],
            'fasta_seq': fasta_seq,
            'file_name': file_name,
            'job_id': 'None',
            'job_status': 'Initializing_SQS',
            'model_preset': model_preset,
            'db_preset': db_preset,
            'num_multimer_predictions_per_model':num_multimer_predictions_per_model,
            'max_template_date': max_template_date,
            'que': data['que'],
            'time': timestamp,
            'gpu': gpu,
            'comment': comment,
            'run_relax':run_relax
        }

        Items.append(Item)
        
    return Items

def method_post(event):
    try:
        Items = check_body(event)
    except Exception as e:
        print('body check failed!')
        raise Exception(e.args)
        # return str(Exception)

    print('body check pass~')
    messages = 'body check pass~.\n'
    for Item in Items:
        response_ddb = table.put_item(Item=Item)
        print('write to ddb',response_ddb)
        
        messages = messages+submit_sqs(Item,'POST')

    return messages

def method_delete(id):
    # DELETE ALL
    if id == '':
        messages = "Deleting all finished and failed jobs.\n\n"
        response_ddb = table.scan()
        for Item in response_ddb['Items']:
            id = Item['id']
            messages = messages + submit_sqs(id,'DELETE')
        return messages
            
    # DELETE ONE
    else:
        response_ddb = table.get_item(Key={'id': id})
        if 'Item' not in response_ddb:
            raise Exception("No such job id to terminate\n")
        else:
            job_status = (response_ddb)['Item']['job_status']
            if (job_status != 'SUCCEEDED' and job_status != 'FAILED'):
                raise Exception("You can't DELETE a "+job_status+" job, please use CANCEL method.\n")
                
            return submit_sqs(id,'DELETE')
            
def method_cancel(id):
    # CANCEL ALL
    if id == '':

        messages = "Canceling all running jobs.\n\n"
        response_ddb = table.scan()
        for Item in response_ddb['Items']:
            id = Item['id']
            messages = messages + submit_sqs(id,'CANCEL')
        return messages
            
    # CANCEL ONE
    else:
        response_ddb = table.get_item(Key={'id': id})
        if 'Item' not in response_ddb:
            raise Exception("No such job id to terminate\n")
        else:
            job_status = (response_ddb)['Item']['job_status']
            if (job_status == 'SUCCEEDED' or job_status == 'FAILED'):
                raise Exception("You can't CANCEL a "+job_status+" job, please use DELETE method.\n")
            return submit_sqs(id,'CANCEL')    

def lambda_handler(event, context):
    
    print(event) # For debug
    method = eval(json.dumps(event['requestContext']['http']['method'])) # HTTP method
    
    if method == 'POST':
        try:
            messages =  method_post(event)
        except Exception as e:
            messages = e.args[0][0]

    elif method  == 'DELETE':
        id = json.dumps(event['requestContext']['http']['path']).strip('"/')
        try:
            messages =  method_delete(id)
        except Exception as e:
            messages = e.args[0]
    elif method == 'CANCEL':
        id = json.dumps(event['requestContext']['http']['path']).strip('"/')
        try:
            messages =  method_cancel(id)
        except Exception as e:
            messages = e.args[0]
    else:
        return  ('Unknown method, Please use POST / DELETE / CANCEL instead.\n')
    return messages