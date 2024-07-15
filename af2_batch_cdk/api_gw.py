from constructs import Construct
import os

from aws_cdk import (
    App, Stack,Duration,CfnOutput,RemovalPolicy,
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
    aws_events_targets as targets,
    aws_apigatewayv2 as apigatewayv2
)

from aws_cdk.aws_apigatewayv2_authorizers import HttpLambdaAuthorizer,HttpLambdaResponseType
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration

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
            removal_policy=RemovalPolicy.DESTROY,
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING,
                
            )
        )

        queue = sqs.Queue(self, "Alphafold2SQSQueue")

        # create IAM role for auth lambda.
        auth_lambda_role = iam.Role(
            self,'Alphafold2IAMAuthLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for auth lambda,',
        )

        auth_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))

        # create IAM role for check request lambda.
        check_request_lambda_role = iam.Role(
            self,'Alphafold2IAMCheckRequestLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for check request lambda.',
        )

        check_request_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        check_request_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        check_request_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        check_request_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role for query result lambda.
        query_status_lambda_role = iam.Role(
            self,'Alphafold2IAMQueryStatusLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for query status lambda.',
        )

        query_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        query_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsReadOnlyAccess'))
        query_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        query_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        query_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))


        # create IAM role for submit job lambda.
        submit_job_lambda_role = iam.Role(
            self,'Alphafold2IAMSubmitJobLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for submit job lambda.',
        )

        submit_job_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        submit_job_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        submit_job_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        submit_job_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))
        submit_job_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role for track status lambda.
        track_status_lambda_role = iam.Role(
            self,'Alphafold2IAMTrackStatusLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for track status lambda.',
        )

        track_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        track_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        track_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        track_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        track_status_lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))

        # create Auth Lambda 
        auth_lambda = _lambda.Function(self, "Alphafold2AuthLambda",
                                              runtime=_lambda.Runtime.NODEJS_18_X,
                                              handler="index.handler",
                                              role = auth_lambda_role,
                                              description = "Api Gateway Auth",
                                              code=_lambda.Code.from_asset("./lambda/auth")
                                              )

        auth_lambda.add_environment("AUTH_KEY", auth_key)

        # create check request Lambda
        check_request_lambda = _lambda.Function(self, "Alphafold2CheckRequestLambda",
                                              runtime=_lambda.Runtime.PYTHON_3_11,
                                              handler="lambda_function.lambda_handler",
                                              role = check_request_lambda_role,
                                              timeout = Duration.seconds(30),
                                              description = "Receive not-GET method HTTP request, send messages to SQS",
                                              code=_lambda.Code.from_asset("./lambda/check_request"))

        check_request_lambda.add_environment("TABLE_NAME", ddb_table.table_name)
        check_request_lambda.add_environment("S3_BUCKET", self.bucket.bucket_name)
        check_request_lambda.add_environment("SQS_QUEUE", queue.queue_url)

        # create query status Lambda
        query_status_lambda = _lambda.Function(self, "Alphafold2QueryStatusLambda",
                                              runtime=_lambda.Runtime.PYTHON_3_11,
                                              handler="lambda_function.lambda_handler",
                                              role = query_status_lambda_role,
                                              timeout = Duration.seconds(30),
                                              description = "Receive GET method HTTP request, query DynamoDB",
                                              code=_lambda.Code.from_asset("./lambda/query_status"))

        query_status_lambda.add_environment("TABLE_NAME", ddb_table.table_name)

        # create submit job Lambda
        submit_job_lambda = _lambda.Function(self, "Alphafold2SubmitJobLambda",
                                              runtime=_lambda.Runtime.PYTHON_3_11,
                                              handler="lambda_function.lambda_handler",
                                              role = submit_job_lambda_role,
                                              timeout = Duration.seconds(30),
                                              description = "Receive SQS messages, Submit to Batch",
                                              code=_lambda.Code.from_asset("./lambda/submit_job"))

        submit_job_lambda.add_environment("TABLE_NAME", ddb_table.table_name)
        submit_job_lambda.add_environment("S3_BUCKET", self.bucket.bucket_name)
        submit_job_lambda.add_environment("SQS_QUEUE", queue.queue_url)  
        submit_job_lambda.add_environment("JOB_DEFINITION_NAME", self.job_Definition_name)

        # create sqs invoker
        submit_job_lambda.add_event_source(eventsources.SqsEventSource(queue))

        # create track status Lambda
        track_status_lambda = _lambda.Function(self, "Alphafold2TrackStatusLambda",
                                              runtime=_lambda.Runtime.PYTHON_3_11,
                                              handler="lambda_function.lambda_handler",
                                              role = track_status_lambda_role,
                                              timeout = Duration.seconds(30),
                                              description = "Track job status, update dynamodb and send messages to SNS",
                                              code=_lambda.Code.from_asset("./lambda/track_status"))

        track_status_lambda.add_environment("TABLE_NAME", ddb_table.table_name)
        track_status_lambda.add_environment("SNS_ARN", sns_topic.topic_arn)
        track_status_lambda.add_environment("S3_BUCKET", self.bucket.bucket_name)


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
                            "id"
                        ],
                            "value": [{
          "exists": True
        }]
                        }
                    }
                }
            )
        )

        Batch_status_change_rule.add_target(
            targets.LambdaFunction(
                track_status_lambda,
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
            handler = auth_lambda
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
            handler=check_request_lambda
        )
        GET_intergation = HttpLambdaIntegration(
            "all-Get method",
            handler=query_status_lambda
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