from constructs import Construct
import os

from aws_cdk import (
    App, Stack,Duration,CfnOutput,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_ecr as ecr,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_fsx as fsx,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as eventsources,
    aws_s3_deployment as s3deploy,
    aws_events_targets as targets
)

from aws_cdk import aws_apigatewayv2_alpha as apigatewayv2
from aws_cdk.aws_apigatewayv2_authorizers_alpha import HttpLambdaAuthorizer,HttpLambdaResponseType
from aws_cdk.aws_apigatewayv2_integrations_alpha import HttpLambdaIntegration

account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

class APIGWCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,sns_topic, auth_key,tag,**kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.job_Definition_name = 'af2'

        # create a s3 bucket
        self.bucket = s3.Bucket(
            self,"Alphafold2S3Bucket-",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # removal_policy=cdk.RemovalPolicy.DESTROY,
            # auto_delete_objects=True
        )

        s3deploy.BucketDeployment(self, "DeployFastaSample",
            sources=[s3deploy.Source.asset("./notebook/input/")],
            destination_bucket= self.bucket ,
            destination_key_prefix="input/"
        )

        ddb_table = dynamodb.Table(
            self,'Alphafold2DDBTable-',
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING,
                
            )
        )

        queue = sqs.Queue(self, "Alphafold2SQSQueue")

        # create IAM role 0
        role0 = iam.Role(
            self,'Alphafold2IAMrole0',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_0',
        )

        role0.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))

        # create IAM role 1
        role1 = iam.Role(
            self,'Alphafold2IAMrole1',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_1',
        )

        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role 2
        role2 = iam.Role(
            self,'Alphafold2IAMrole2',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_2',
        )

        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsReadOnlyAccess'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))


        # create IAM role 3
        role3 = iam.Role(
            self,'Alphafold2IAMrole3',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_3',
        )

        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role 4
        role4 = iam.Role(
            self,'Alphafold2IAMrole4',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_4',
        )

        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))

        # create Lambda 0
        lambda_0 = _lambda.Function(self, "Alphafold2Lambda0",
                                              runtime=_lambda.Runtime.NODEJS_14_X,
                                              handler="index.handler",
                                              role = role0,
                                              description = "Api Gateway Auth",
                                              code=_lambda.Code.from_asset("./lambda/lambda_0")
                                              )

        lambda_0.add_environment("AUTH_KEY", auth_key)

        # create Lambda 1
        lambda_1 = _lambda.Function(self, "Alphafold2Lambda1-",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role1,
                                              timeout = Duration.seconds(30),
                                              description = "Receive not-GET method HTTP request, send messages to SQS",
                                              code=_lambda.Code.from_asset("./lambda/lambda_1"))

        lambda_1.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_1.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_1.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 2
        lambda_2 = _lambda.Function(self, "Alphafold2Lambda2-",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role2,
                                              timeout = Duration.seconds(30),
                                              description = "Receive GET method HTTP request, query DynamoDB",
                                              code=_lambda.Code.from_asset("./lambda/lambda_2"))

        lambda_2.add_environment("TABLE_NAME", ddb_table.table_name)

        # create Lambda 3
        lambda_3 = _lambda.Function(self, "Alphafold2Lambda3-",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role3,
                                              timeout = Duration.seconds(30),
                                              description = "Receive SQS messages, Submit to Batch",
                                              code=_lambda.Code.from_asset("./lambda/lambda_3"))

        lambda_3.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_3.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_3.add_environment("SQS_QUEUE", queue.queue_url)  
        lambda_3.add_environment("JOB_DEFINITION_NAME", self.job_Definition_name)

        # create sqs invoker
        lambda_3.add_event_source(eventsources.SqsEventSource(queue))

        # create Lambda 4
        lambda_4 = _lambda.Function(self, "Alphafold2Lambda4-",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role4,
                                              timeout = Duration.seconds(30),
                                              description = "Track job status, update dynamodb and send messages to SNS",
                                              code=_lambda.Code.from_asset("./lambda/lambda_4"))

        lambda_4.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_4.add_environment("SNS_ARN", sns_topic.topic_arn)
        lambda_4.add_environment("S3_BUCKET", self.bucket.bucket_name)


        Batch_status_change_rule = events.Rule(
            self,"Alphafold2BatchStatusChangeRule-",
            description = "Track batch job status change",
            event_pattern = events.EventPattern(
                source = ["aws.batch"],
                detail_type = ["Batch Job State Change"],
                detail = {
                    "container": {
                        "environment": {
                            "name": [
                            "AWS-GCR-HCLS-Solutions"
                        ],
                            "value": [
                            tag
                        ]
                        }
                    }
                }
            )
        )

        Batch_status_change_rule.add_target(
            targets.LambdaFunction(
                lambda_4,
                max_event_age=Duration.hours(2), # Otional: set the maxEventAge retry policy
                retry_attempts=2
            )
        )

        # create api-gateway
        apigw_auth = HttpLambdaAuthorizer(
            "Alphafold2Auth",
            authorizer_name = 'Alphafold2Auth',
            response_types = [HttpLambdaResponseType('SIMPLE')],
            # payload_format_version = apigatewayv2.AuthorizerPayloadVersion('VERSION_2_0'),
            handler = lambda_0
        )

        if len(auth_key)!=0:
            apigw = apigatewayv2.HttpApi(
                self,'Alphafold2ApiGateway',
                api_name = 'Alphafold2ApiGateway',
                default_authorizer = apigw_auth
            )
        else:
            apigw = apigatewayv2.HttpApi(
                self,'Alphafold2ApiGateway',
                api_name = 'Alphafold2ApiGateway'
            )

        not_GET_intergation = HttpLambdaIntegration(
            "not-GET method",
            handler=lambda_1
        )
        GET_intergation = HttpLambdaIntegration(
            "all-Get method",
            handler=lambda_2
        )

        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.GET],
            integration = GET_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.GET],
            integration = GET_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.POST],
            integration = not_GET_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.DELETE],
            integration = not_GET_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.ANY],# for CANCEL method
            integration = not_GET_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.DELETE],
            integration = not_GET_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.ANY],# for CANCEL method
            integration = not_GET_intergation
        )

        CfnOutput(
            self,"af2-S3",
            description="S3",
            value=self.bucket.bucket_arn,
        )

        CfnOutput(
            self,"af2-APIGW",
            description="APIGW",
            value=apigw.api_endpoint,
        )