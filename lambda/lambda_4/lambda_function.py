import json
import os
import boto3
from pyh import *

# created by sunliang
# modified by wutong

# 指定要分享的文件名, type = str，分享全部文件用 '*'
fileIndex = '*'
#包含文件下载地址列表的html文件名
html = 'index.html'

s3Client = boto3.client('s3')

snsClient = boto3.client('sns')
sns_arn = os.environ['SNS_ARN']
batch = boto3.client('batch')

dynamodb = boto3.resource('dynamodb')
ddb = dynamodb.Table(os.environ['TABLE_NAME'])

def getSharedFileList(fileBucket, dirPrefix):
    fileList = []
    # 原文件名为*则查文件列表，否则就查单个文件
    try:
        if fileIndex == '*':
            response_fileList = s3Client.list_objects_v2(
                Bucket = fileBucket,
                Prefix = dirPrefix,
                MaxKeys = 1000
            )
            for n in response_fileList['Contents']:
                if n['Key'][-1] != '/':      # Key以'/'结尾的是子目录，不处理
                    presignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': fileBucket,
                            'Key': n['Key']
                        })
                    fileList.append({
                        'Key': n['Key'],
                        'Url': presignUrl,
                        'Size': n['Size']
                    })
            
            while response_fileList['IsTruncated']:
                response_fileList = s3Client.list_objects_v2(
                    Bucket = fileBucket,
                    Prefix = dirPrefix,
                    MaxKeys = 1000,
                    ContinuationToken = response_fileList['NextContinuationToken']
                )
                if n['Key'][-1] != '/':      # Key以'/“结尾的是子目录，不处理
                    presignUrl = s3Client.generate_presigned_url(
                        'get_object',
                        Params = {
                            'Bucket': fileBucket,
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
                            'Bucket': fileBucket,
                            'Key': fileKey
                        })
            response_fileList = s3Client.head_object(
                Bucket = fileBucket,
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
    #page.addObj('<script src="http://code.jquery.com/jquery-latest.js"></script>')
    # 输出 html到string
    result = page.printStr()
    return result

# Main
def lambda_handler(event, context):
    # print (event)
    for record in event['Records']:
        fileBucket = record['s3']['bucket']['name']
        dirPrefix = (record['s3']['object']['key']).split('.')[0]
        fileName = record['s3']['object']['key'].split('/')[1]

        print('Bucket: ', fileBucket)
        print('Dir: ', dirPrefix)
        if fileBucket.strip() == '': 
            print('[ERROR] Bucket name is not valid')
            os._exit(0)
    
        # 检查bucket能否写入
        try:
            testKey = os.path.join(dirPrefix, 'access_test')
            s3Client.put_object(
                Bucket = fileBucket,
                Key = testKey,
                Body = 'access_test_content'
            )
            s3Client.delete_object(
                Bucket = fileBucket,
                Key = testKey
            )
        except Exception as e:
            print('[ERROR] Not authorized to write to destination bucket/prefix. Err: ', e)
            os._exit(0)
    
        # 获取分享的文件列表
        shareFileList = getSharedFileList(fileBucket, dirPrefix)
        # 生成包含文件下载地址列表的html文件
        htmlStr = generteHtml(shareFileList)
        # 上传html文件到分享目录
        if htmlStr.strip() != '':
            htmlKey = os.path.join(dirPrefix, html)
            s3Client.put_object(
                Bucket = fileBucket,
                Key = htmlKey,
                Body = htmlStr
            )
        else:
            print('[ERROR] Html is blank')
            os._exit(0)
    
        # 生成分享url
        htmlPresignUrl = s3Client.generate_presigned_url(
                            'get_object',
                            Params = {
                                'Bucket': fileBucket,
                                'Key': htmlKey
                            })
        print('htmlPresignUrl: ', htmlPresignUrl)

        # get id
        id = s3Client.head_object(Bucket=fileBucket, Key=record['s3']['object']['key'])['Metadata']['id']
        
        response_ddb = ddb.get_item(Key={'id':id})
        job_id = response_ddb['Item']['job_id']
        response_batch = batch.describe_jobs(
            jobs=[
                job_id,
            ]
        )
        
        jobName = response_batch['jobs'][0]['jobName']

        # get cost
        startedAt = response_batch['jobs'][0]['startedAt']
        stoppedAt = response_batch['jobs'][0]['stoppedAt']
        cost = round((stoppedAt-startedAt)/1000)

        if record['awsRegion'] == 'cn-north-1' or record['awsRegion'] == 'cn-northwest-1':
            messageStr = 'Total runtime is '+str(cost)+'s.\n\nIn AWS China,Presigned URLs work only if the resource owner has an ICP license , otherwise, please use aws cli $aws s3 sync s3://'+fileBucket+'/'+dirPrefix+' ./ to download entire foleder'+'\n\nDownload files from the html: ' + htmlPresignUrl
        else:
            messageStr = 'Total runtime is '+str(cost)+'s.\n\nYou can download files from the html: ' + htmlPresignUrl+'.\n\nYou can alsp use aws cli $aws s3 sync s3://'+fileBucket+'/'+dirPrefix+' ./ to download entire foleder'
        response_sns = snsClient.publish(
            TopicArn = sns_arn,
            Message = messageStr,
            Subject = jobName +"'s result data is now available for download"
        )
        print('Sns publish response: ', response_sns)
        

        # return usage
        
        # update dynamodb
        response_ddb = ddb.update_item(
            Key={
                'id': id
            },
            UpdateExpression='SET s3_url = :s3_url,job_status = :job_status,cost = :cost',
            ExpressionAttributeValues={
                ':s3_url': htmlPresignUrl,
                ':job_status': 'allset',
                ':cost': cost
            }
            # ReturnValues: "UPDATED_NEW"
        )
        
        print ("response_ddb from update_item"+str(response_ddb))
        
        return response_ddb
