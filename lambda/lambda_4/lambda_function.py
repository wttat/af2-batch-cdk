import json
import os
import boto3
from pyh import *

fileIndex = '*'
html = 'index.html'

s3Client = boto3.client('s3')
bucket_name = os.environ['S3_BUCKET']

snsClient = boto3.client('sns')
sns_arn = os.environ['SNS_ARN']
batch = boto3.client('batch')

dynamodb = boto3.resource('dynamodb')
ddb = dynamodb.Table(os.environ['TABLE_NAME'])

expiretime = 86400 # 24h*60min*60s = 1day

def getSharedFileList(bucket_name, dirPrefix):
    fileList = []
    try:
        if fileIndex == '*':
            response_fileList = s3Client.list_objects_v2(
                Bucket = bucket_name,
                Prefix = dirPrefix,
                MaxKeys = 1000
            )
            for n in response_fileList['Contents']:
                if n['Key'][-1] != '/':      
                    presignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': bucket_name,
                            'Key': n['Key']
                        })
                    fileList.append({
                        'Key': n['Key'],
                        'Url': presignUrl,
                        'Size': n['Size']
                    })
            
            while response_fileList['IsTruncated']:
                response_fileList = s3Client.list_objects_v2(
                    Bucket = bucket_name,
                    Prefix = dirPrefix,
                    MaxKeys = 1000,
                    ContinuationToken = response_fileList['NextContinuationToken']
                )
                if n['Key'][-1] != '/':      
                    presignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': bucket_name,
                            'Key': n['Key']
                        })
                    fileList.append({
                        'Key': n['Key'],
                        'Url': presignUrl,
                        'Size': n['Size']
                    })
        else:
            fileKey = os.path.join(dirPrefix, fileIndex)
            presignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': bucket_name,
                            'Key': fileKey
                        },
                        ExpiresIn = expiretime
                        )
            response_fileList = s3Client.head_object(
                Bucket = bucket_name,
                Key = fileKey
            )
            fileList = [{
                'Key': fileKey,
                'Url': presignUrl,
                'Size': response_fileList['ContentLength']
            }]
    except Exception as e:
        print('[ERROR] Can not get file bucket/prefix. Err: ', e)
        os._exit(0)
    return fileList

def generteHtml(fileList):
    page = PyH('Shared Files')
    page << h2('Shared Files')

    mytab = page << table()
    th = mytab << tr()
    th << td(b('Name')) + td(b('Size (Bytes)')) + td(b('Link'))

    for file in fileList:
        tr1 = mytab << tr()
        tr1 << td(file['Key']) + td(str(file['Size'])) + td(a('Download', href = file['Url']))

    result = page.printStr()
    return result


def check_id(id):
    # Check whether this job status change event belongs to Alphafold2 solution
    if id == '':
        print("Cannot found the id field, This batch job does not belong to Alphafold2 solution")
        return 1
    else:
        try:
            response_ddb = ddb.get_item(Key={'id':id})
        except:
            print("Cannot found this record in dynamodb from id: ",id)
            return 1
        else:
            print("Found the id:",id ,"in dynamodb.")
            return 0

def job_status_update_others(id,job_status):
    # Only update the job status in ddb.
    response_ddb = ddb.update_item(
        Key={
            'id': id
        },
        UpdateExpression='SET job_status = :job_status',
        ExpressionAttributeValues={
            ':job_status': job_status
        }
    )
    print ("Update dynamodb for id: "+id+"completed.")
    
def job_status_failed_others(id,statusReason):
    # Update the job status in ddb first.
    response_ddb = ddb.get_item(Key={'id': id})
    fasta_file_name = response_ddb['Item']['file_name']
    response_ddb = ddb.update_item(
        Key={
            'id': id
        },
        UpdateExpression='SET failed_Reason = :failed_Reason,job_status = :job_status',
        ExpressionAttributeValues={
            ':failed_Reason': statusReason,
            ':job_status': 'FAILED'
        }
    )
    
    print ("Update dynamodb for id: "+id+"completed.")
    
    # Send SNS message.
    messageStr = 'Job failed,id:' + id + '.\nFailed reason: ' + statusReason + '.\n Please contact admin.'
    response_sns = snsClient.publish(
        TopicArn = sns_arn,
        Message = messageStr,
        Subject = 'Alphafold2'+fasta_file_name+' job failed'
    )
    print('Sns publish response: ', response_sns)
    
def job_status_succeeded_others(id):
    # First check whether this job is truly succeeded.
    response_ddb = ddb.get_item(Key={'id': id})
    fasta_file_name = response_ddb['Item']['file_name']
    dirPrefix = 'output/'+fasta_file_name.split('.')[0]
    tar_gz = 'output/'+fasta_file_name.split('.')[0]+'.tar'+'.gz'
    
    # Check S3 permission.
    if bucket_name.strip() == '': 
        print('[ERROR] Bucket name is not valid')
        os._exit(0)
    try:
        testKey = os.path.join(dirPrefix, 'access_test')
        s3Client.put_object(
            Bucket = bucket_name,
            Key = testKey,
            Body = 'access_test_content'
        )
        s3Client.delete_object(
            Bucket = bucket_name,
            Key = testKey
        )
    except Exception as e:
        print('[ERROR] Not authorized to write to destination bucket/prefix. Err: ', e)
        os._exit(0)
    
    # Check pdb file.
    try:
        s3Client.get_object(
            Bucket = bucket_name,
            Key = tar_gz
            )
    except:
        print("no tar.gz file found for job id :",id, "something wrong, change status from succeeded to failed")
        job_status_failed_others(id,"no tar.gz file found")
        return
    else:
        print("found tar.gz file for job id :",id)
    
    # Generate s3 pre-signed url html
    shareFileList = getSharedFileList(bucket_name, dirPrefix)
    htmlStr = generteHtml(shareFileList)
    if htmlStr.strip() != '':
        htmlKey = os.path.join(dirPrefix, html)
        s3Client.put_object(
            Bucket = bucket_name,
            Key = htmlKey,
            Body = htmlStr
        )
    else:
        print('[ERROR] Html is blank')
        os._exit(0)
        
    htmlPresignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': bucket_name,
                            'Key': htmlKey
                        },
                        ExpiresIn = expiretime
                        
                        )
    print('htmlPresignUrl: ', htmlPresignUrl)
    
    # Get job runtime
    job_id = response_ddb['Item']['job_id']
    response_batch = batch.describe_jobs(
        jobs=[
            job_id,
        ]
    )
        
    jobName = response_batch['jobs'][0]['jobName']

    startedAt = response_batch['jobs'][0]['startedAt']
    stoppedAt = response_batch['jobs'][0]['stoppedAt']
    cost = round((stoppedAt-startedAt)/1000)

    if os.environ['AWS_REGION'] == 'cn-north-1' or os.environ['AWS_REGION'] == 'cn-northwest-1':
        messageStr = 'Total runtime is '+str(cost)+'s.\n\nIn AWS China,Presigned URLs work only if the resource owner has an ICP license , otherwise, please use aws cli $aws s3 sync s3://'+bucket_name+'/'+dirPrefix+' ./ to download entire foleder'+'\n\nDownload files from the html: ' + htmlPresignUrl
    else:
        messageStr = 'Total runtime is '+str(cost)+'s.\n\nYou can download files from the html: ' + htmlPresignUrl+'.\n\nYou can alsp use aws cli $aws s3 sync s3://'+bucket_name+'/'+dirPrefix+' ./ to download entire foleder'
    response_sns = snsClient.publish(
        TopicArn = sns_arn,
        Message = messageStr,
        Subject = jobName +"'s result data is now available for download"
    )
    print('Sns publish response: ', response_sns)

    response_ddb = ddb.update_item(
        Key={
            'id': id
        },
        UpdateExpression='SET s3_url = :s3_url,job_status = :job_status,cost = :cost',
        ExpressionAttributeValues={
            ':s3_url': htmlPresignUrl,
            ':job_status': 'SUCCEEDED',
            ':cost': cost
        }
    )
        
    print ("Update dynamodb for id: "+id+"completed.")

    
def lambda_handler(event, context):
    
    # Check id validity.
    id = ''
    for i in event['detail']['container']['environment']:
        if i['name'] == 'id':
            id = i['value']
    if check_id(id) == 1:
        return
    
    job_status = event['detail']['status']
    print("Found job status:",job_status)
    
    if job_status == 'SUCCEEDED':
        job_status_succeeded_others(id)
    elif job_status == 'FAILED':
        statusReason = event['detail']['statusReason']
        job_status_failed_others(id,statusReason)
    else:
        job_status_update_others(id,job_status)