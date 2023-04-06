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

    def __init__(self, scope: Construct, construct_id: str,sns_topic, auth_key,**kwargs) -> None:
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

        # create IAM role for Lambda Authorizer
        iam_role_LambdaAuthorizer = iam.Role(
            self,'Alphafold2IAMRoleforLambdaAuthorizer',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description ='IAM role for Lambda Authorizer',
        )

        iam_role_LambdaAuthorizer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))

        # create IAM role for Lambda JobSubmit
        iam_role_LambdaJobSubmit = iam.Role(
            self,'Alphafold2IAMRoleForLambdaJobSubmit',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description ='IAM role for Lambda JobSubmit',
        )

        iam_role_LambdaJobSubmit.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        iam_role_LambdaJobSubmit.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        iam_role_LambdaJobSubmit.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        iam_role_LambdaJobSubmit.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role for Lambda JobStatusQuery
        iam_role_LambdaJobStatusQuery = iam.Role(
            self,'Alphafold2IAMRoleForLambdaStatusQuery',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for Lambda JobStatusQuery',
        )

        iam_role_LambdaJobStatusQuery.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        iam_role_LambdaJobStatusQuery.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsReadOnlyAccess'))
        iam_role_LambdaJobStatusQuery.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        iam_role_LambdaJobStatusQuery.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        iam_role_LambdaJobStatusQuery.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))


        # create IAM role for Lambda SQSCustomer
        iam_role_LambdaSQSCustomer = iam.Role(
            self,'Alphafold2IAMRoleForLambdaSQSCustomer',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for Lambda SQSCustomer',
        )

        iam_role_LambdaSQSCustomer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        iam_role_LambdaSQSCustomer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        iam_role_LambdaSQSCustomer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        iam_role_LambdaSQSCustomer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        iam_role_LambdaSQSCustomer.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role for Lambda JobStatusTracker
        iam_role_LambdaJobStatusTracker = iam.Role(
            self,'Alphafold2IAMRoleRotLambdaJobStatusTracker',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for Lambda JobStatusTracker',
        )

        iam_role_LambdaJobStatusTracker.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        iam_role_LambdaJobStatusTracker.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        iam_role_LambdaJobStatusTracker.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        iam_role_LambdaJobStatusTracker.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        iam_role_LambdaJobStatusTracker.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))

        # create Lambda Authorizer
        lambda_Authorizer = _lambda.Function(self, "Alphafold2LambdaAuthorizer",
                                              runtime=_lambda.Runtime.NODEJS_14_X,
                                              handler="index.handler",
                                              role = iam_role_LambdaAuthorizer,
                                              description = "Lambda For API Gateway Auth",
                                              code=_lambda.Code.from_asset("./lambda/Authorizer")
                                              )

        lambda_Authorizer.add_environment("AUTH_KEY", auth_key)

        # create Lambda JobSubmit
        lambda_JobSubmit = _lambda.Function(self, "Alphafold2LambdaJobSubmit",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = iam_role_LambdaJobSubmit,
                                              timeout = Duration.seconds(30),
                                              description = "Receive non-Get method HTTP request, send messages to SQS",
                                              code=_lambda.Code.from_asset("./lambda/JobSubmit"))

        lambda_JobSubmit.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_JobSubmit.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_JobSubmit.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda JobStatusQuery
        lambda_JobStatusQuery = _lambda.Function(self, "Alphafold2LambdaJobStatusQuery",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = iam_role_LambdaJobStatusQuery,
                                              timeout = Duration.seconds(30),
                                              description = "Receive GET method HTTP request, query DynamoDB",
                                              code=_lambda.Code.from_asset("./lambda/JobStatusQuery"))

        lambda_JobStatusQuery.add_environment("TABLE_NAME", ddb_table.table_name)

        # create Lambda SQSCustomer
        lambda_SQSCustomer = _lambda.Function(self, "Alphafold2LambdaSQSCustomer",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = iam_role_LambdaSQSCustomer,
                                              timeout = Duration.seconds(30),
                                              description = "Receive SQS messages, Submit to Batch",
                                              code=_lambda.Code.from_asset("./lambda/SQSCustomer"))

        lambda_SQSCustomer.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_SQSCustomer.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_SQSCustomer.add_environment("SQS_QUEUE", queue.queue_url)  
        lambda_SQSCustomer.add_environment("JOB_DEFINITION_NAME", self.job_Definition_name)

        # create sqs invoker
        lambda_SQSCustomer.add_event_source(eventsources.SqsEventSource(queue))

        # create Lambda JobStatusTracker
        lambda_JobStatusTracker = _lambda.Function(self, "Alphafold2LambdaJobStatusTracker",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = iam_role_LambdaJobStatusTracker,
                                              timeout = Duration.seconds(30),
                                              description = "Track job status, update dynamodb and send messages to SNS",
                                              code=_lambda.Code.from_asset("./lambda/JobStatusTracker"))

        lambda_JobStatusTracker.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_JobStatusTracker.add_environment("SNS_ARN", sns_topic.topic_arn)
        lambda_JobStatusTracker.add_environment("S3_BUCKET", self.bucket.bucket_name)


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
                            "Alphafold2"
                        ]
                        }
                    }
                }
            )
        )

        Batch_status_change_rule.add_target(
            targets.LambdaFunction(
                lambda_JobStatusTracker,
                max_event_age=Duration.hours(2),
                retry_attempts=2
            )
        )

        # create api-gateway
        apigw_auth = HttpLambdaAuthorizer(
            "Alphafold2Auth",
            authorizer_name = 'Alphafold2Auth',
            response_types = [HttpLambdaResponseType('SIMPLE')],
            # payload_format_version = apigatewayv2.AuthorizerPayloadVersion('VERSION_2_0'),
            handler = lambda_Authorizer,
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
            handler=lambda_JobSubmit
        )
        GET_intergation = HttpLambdaIntegration(
            "all-Get method",
            handler=lambda_JobStatusQuery
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