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
    print(event)
    method = eval(json.dumps(event['requestContext']['http']['method']))

    if method == 'POST':
        # check for body

        messages = ""
        Items = []

        try:
            datas = json.loads(event['body'])
        except:
            return 'Please check HTTP body.It should in json.\n'
        else:
            datas = json.loads(event['body'])

        for data in datas:

            # check for file
            try:
                data['file_name']
            except:
                return 'You need to specific the fasta file name.\n'

            file_name = data['file_name']
            key = prefix+file_name

            # return key

            # check file path
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                return ('The fatsa file path is not correct, please put it in s3://'+bucket+'/'+prefix+'\n')
            print('fasta found')



            id = str(uuid.uuid4())
            now = time.asctime()

            # decouple Item for both SQS and dynamoDB usage

            try:
                data['fasta']
                data['que']
            except:
                return 'You need to at least specific the fasta and que parameters.\n'

            # TODO check p4 auto
            if data['que'] != 'high' and data['que'] != 'mid' and data['que'] != 'low' and data['que'] != 'p4':
                return 'The job queue should be high or mid or low or p4(depends on region) .\n'

            max_template_date = ''
            try:
                data['max_template_date']
            except:
                print('no max_template_date,using dafault max_template_date 2021-11-01')
                max_template_date = '2021-11-01'
            else:
                max_template_date = data['max_template_date']
            print(max_template_date)

            model_preset = ''
            try:
                data['model_preset']
            except:
                return 'You need to specific the model preset.\n'
            else:
                if data['model_preset'] != 'monomer' and data['model_preset'] != 'monomer_casp14' and data['model_preset'] != 'monomer_ptm' and data['model_preset'] != 'multimer':
                    return 'The model preset shoudl be monomer or monomer_casp14 or monomer_ptm or multimer'
                else:
                    model_preset = data['model_preset']
            print(model_preset)

            # get fasta seq
            if model_preset != 'multimer':
                s3.download_file(bucket, key, '/tmp/'+file_name)
                fasta_seq = linecache.getline(
                    '/tmp/'+file_name, line_number).strip()
            else:
                fasta_seq = "This is a multimer seq"

            db_preset = ''
            try:
                data['db_preset']
            except:
                print('no preset,using dafault preset full')
                db_preset = 'full_dbs'
            else:
                if data['db_preset'] != 'full_dbs' and data['db_preset'] != 'reduced_dbs':
                    return 'The db preset shoudl be full_dbs or reduced_dbs'
                else:
                    db_preset = data['db_preset']
            print(db_preset)

            is_prokaryote_list = ''
            try:
                data['is_prokaryote_list']
            except:
                print('no preset,using dafault preset false')
                is_prokaryote_list = 'false'
            else:
                if data['is_prokaryote_list'] != 'true' and data['is_prokaryote_list'] != 'false':
                    return 'The is_prokaryote_list shoudl be true or false'
                elif data['is_prokaryote_list'] == 'true' and model_preset != 'multimer':
                    return 'is_prokaryote_list only could be true if model_preset is multimer'
                else:
                    is_prokaryote_list = data['is_prokaryote_list']
            print(is_prokaryote_list)

            run_relax = ''
            try:
                data['run_relax']
            except:
                print('no run_relax,using dafault preset true')
                run_relax = 'true'
            else:
                if data['run_relax'] != 'true' and data['run_relax'] != 'false':
                    return 'The run_relax shoudl be true or false'
                else:
                    run_relax = data['run_relax']
            print(run_relax)

            comment = ''
            try:
                data['comment']
            except:
                print('no comment')
            else:
                comment = data['comment']
            print(comment)

            gpu = ''
            try:
                data['gpu']
            except:
                print('no gpu')
                gpu = 1
            else:
                gpu = data['gpu']

            print(gpu)

            if gpu > 1:
                if data['que'] == 'low':
                    return "this que only support 1 GPU"
                if gpu > 4:
                    if data['que'] == 'mid':
                        return "only p3.8xlarge or p4 support more than 4 GPU"
                    if gpu > 8:
                        return "max GPU = 8"

            Item = {
                'id': id,
                'fasta': data['fasta'],
                'fasta_seq': fasta_seq,
                'file_name': file_name,
                'job_id': 'none',
                'job_status': 'starting',
                'model_preset': model_preset,
                'db_preset': db_preset,
                'is_prokaryote_list':is_prokaryote_list,
                'max_template_date': max_template_date,
                'que': data['que'],
                'time': now,
                'gpu': gpu,
                'comment': comment,
                'run_relax':run_relax
            }

            Items.append(Item)
            # return str(type(Item))

        for Item in Items:
            response_ddb = table.put_item(Item=Item)
            print(response_ddb)

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

            print(response_sqs)
            if response_sqs['ResponseMetadata']['HTTPStatusCode'] == 200:
                messages = messages + '\nSuccessful submit Batch job for fasta:' + \
                    Item['fasta'] + ', id:' + Item['id']+'\n\n' + \
                    'Please use $(curl $auth-info $api-gateway-url/' + \
                    Item['id']+') to query this job'+'\n\n'
        return messages

    elif method == 'DELETE' or method == 'CANCEL':

        id = json.dumps(event['requestContext']['http']['path']).strip('"/')

        if id == '':
            if method == 'DELETE':
                messages = "Deleting all finished and failed jobs.\n\n"
            elif method == 'CANCEL':
                messages = "Canceling all running jobs.\n\n"

            response_ddb = table.scan()

            for Item in response_ddb['Items']:
                status = Item['job_status']
                id = Item['id']
                # if status == 'allset' or status == 'failed':
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
                print(response_sqs)
                messages = messages + 'Successfully send ' + \
                    method+' command to all Batch job.\n\n'
            messages = messages + '####\nPlease wait 2min and try again.\n\n'
            return messages

            # return("please specific id for delete or cancel\n")
        else:
            response_ddb = table.get_item(Key={'id': id})
            if 'Item' not in response_ddb:
                return "no such job id to terminate\n"
            else:
                # response_ddb = table.delete_item(Key={'id': id})

                status = (response_ddb)['Item']['job_status']

                if status == 'allset' and method == 'CANCEL':
                    return "This job has completed, you could use delete method to delete all files.\n"

                if status == 'failed' and method == 'CANCEL':
                    return "This job has failed, you could use delete method to delete all files.\n"

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
                print(response_sqs)
                if response_sqs['ResponseMetadata']['HTTPStatusCode'] == 200:
                    return('Success send '+method+' command to Batch job ,id :' + id+' \n####\nPlease wait 2min and try again.\n')
                # return response_sqs

    else:
        return ('Unknown method, Please use POST / DELETE / CANCEL instead.\n')
