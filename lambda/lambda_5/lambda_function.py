import json
import boto3
import os

snsClient = boto3.client('sns')
sns_arn = os.environ['SNS_ARN']

dynamodb = boto3.resource('dynamodb')
ddb = dynamodb.Table(os.environ['TABLE_NAME'])

# for failed job
def lambda_handler(event, context):
    print (event)
    for i in event['detail']['container']['environment']:
        if i['name'] == 'id':
            id = i['value']
    
    statusReason = event['detail']['statusReason']

    # update dynamodb
    response_ddb = ddb.update_item(
        Key={
            'id': id
        },
        UpdateExpression='SET failed_Reason = :failed_Reason,job_status = :job_status',
        ExpressionAttributeValues={
            ':failed_Reason': statusReason,
            ':job_status': 'failed'
        }
        # ReturnValues: "UPDATED_NEW"
    )
    
    print ("response_ddb from update_item"+str(response_ddb))
    
    
    messageStr = 'Job failed,id:' + id + '.\nFailed reason: ' + statusReason
    response_sns = snsClient.publish(
        TopicArn = sns_arn,
        Message = messageStr,
        Subject = 'Af2-batch job failed'
    )
    print('Sns publish response: ', response_sns)
    
    return response_sns