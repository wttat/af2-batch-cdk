from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import (
    core,
    aws_iam,
    aws_s3,
    aws_dynamodb,
    aws_events,
    aws_sns,
    aws_ecr,
    aws_lambda,
    aws_sqs
)

# Set the api-gateway auth_key, it's essential for AWS china if you don't have an ICP.
auth_key = 'af2'
mail_address = '@'

class Af2BatchCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create dynamodb table
        ddb_table = aws_dynamodb.Table(
            self,'af2_ddb',
            partition_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            )
        )

        # create a s3 bucket
        bucket = aws_s3.Bucket(
            self,"af2_bucket",
        )

        #  create a SNS topic
        topic = aws_sns.Topic(self, "Topic",
            display_name="Customer subscription topic"
        )

        #  create a SQS queue
        queue = aws_sqs.Queue(self, "SQSQueue")

        # create IAM role 0
        role0 = aws_iam.Role(
            self,'role_0',
            description =' IAM role for lambda_0',
        )
        role0.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role0_arn = role0.role_arn()

        # create IAM role 1
        role1 = aws_iam.Role(
            self,'role_1',
            description =' IAM role for lambda_1',
        )
        role1.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role1.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role1.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role1.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role1_arn = role1.role_arn()

        # create IAM role 2
        role2 = aws_iam.Role(
            self,'role_2',
            description =' IAM role for lambda_2',
        )
        role2.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role2.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsReadOnlyAccess'))
        role2.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role2.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        role2_arn = role2.role_arn()

        # create IAM role 3
        role3 = aws_iam.Role(
            self,'role_3',
            description =' IAM role for lambda_3',
        )
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role3_arn = role3.role_arn()

        # create IAM role 4
        role4 = aws_iam.Role(
            self,'role_4',
            description =' IAM role for lambda_4',
        )
        role4.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role4.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role4.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role3.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role4_arn = role4.role_arn()

        # create IAM role 5
        role5 = aws_iam.Role(
            self,'role_5',
            description =' IAM role for lambda_5',
        )
        role5.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role5.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role5.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role5_arn = role5.role_arn()

        # create Lambda 0
        lambda_0 = aws_lambda.Function(self, "lambda_0",
                                              runtime=aws_lambda.Runtime.NODEJS_14_X,
                                              handler="index.handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_0"))
        lambda_0.add_environment("AUTH_KEY", auth_key)

        # create Lambda 1
        lambda_1 = aws_lambda.Function(self, "lambda_1",
                                              runtime=aws_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_1"))
        lambda_1.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_1.add_environment("S3_BUCKET", bucket.bucket_name)
        lambda_1.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 2
        lambda_2 = aws_lambda.Function(self, "lambda_2",
                                              runtime=aws_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_2"))
        lambda_2.add_environment("TABLE_NAME", ddb_table.table_name)

        # create Lambda 3
        lambda_3 = aws_lambda.Function(self, "lambda_3",
                                              runtime=aws_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_3"))
        lambda_3.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_3.add_environment("S3_BUCKET", bucket.bucket_name)
        lambda_3.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 4
        lambda_4 = aws_lambda.Function(self, "lambda_4",
                                              runtime=aws_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_4"))
        lambda_4.add_environment("TABLE_NAME", ddb_table.table_name)
        # lambda_4.add_environment("S3_BUCKET", bucket.bucket_name)
        lambda_4.add_environment("SNS_ARN", topic.topic_arn)

        # create Lambda 5
        lambda_5 = aws_lambda.Function(self, "lambda_5",
                                              runtime=aws_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=aws_lambda.Code.asset("./lambda/lambda_5"))
        lambda_5.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_5.add_environment("SNS_ARN", topic.topic_arn)

        # create api-gateway


        # create ECR repo
        repo = aws_ecr.Repository(
            self,'af2',
        )










