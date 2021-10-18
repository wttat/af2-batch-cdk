# from typing import Protocol
import os
from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import (
    core,
)

import aws_cdk.aws_iam as iam
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_events as events
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_fsx as fsx
import aws_cdk.aws_apigatewayv2 as apigatewayv2
import aws_cdk.aws_apigatewayv2_authorizers as apigatewayv2_authorizers
import aws_cdk.aws_apigatewayv2_integrations as apigatewayv2_integrations
import aws_cdk.aws_s3_notifications as s3n
import aws_cdk.aws_lambda_event_sources as eventsources
import aws_cdk.aws_s3_deployment as s3deploy

# get account ID and region
account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]



class APIGWCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,vpc,sns_topic, auth_key,**kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Set the api-gateway auth_key, it's essential for api gateway in AWS china if you don't have an ICP.
        # auth_key = self.node.try_get_context("auth_key") # replace your own
        # auth_key = "af2" # replace your own

        self.job_Definition_name = 'af2'

        # create a s3 bucket
        self.bucket = s3.Bucket(
            self,"BUCKET",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        s3deploy.BucketDeployment(self, "DeployFastaSample",
            sources=[s3deploy.Source.asset("./input/")],
            destination_bucket= self.bucket ,
            destination_key_prefix="input/"
        )

        # create dynamodb table
        ddb_table = dynamodb.Table(
            self,'af2_ddb',
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            )
        )

        #  create a SQS queue
        queue = sqs.Queue(self, "SQSQueue")

        # create IAM role 0
        role0 = iam.Role(
            self,'role_0',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_0',
        )

        role0.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))

        # create IAM role 1
        role1 = iam.Role(
            self,'role_1',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_1',
        )

        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role 2
        role2 = iam.Role(
            self,'role_2',
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
            self,'role_3',
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
            self,'role_4',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_4',
        )

        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))

        # create IAM role 5
        role5 = iam.Role(
            self,'role_5',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_5',
        )

        role5.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole'))
        role5.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role5.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create Lambda 0
        lambda_0 = _lambda.Function(self, "lambda_0",
                                              runtime=_lambda.Runtime.NODEJS_14_X,
                                              handler="index.handler",
                                              role = role0,
                                              description = "For apigw auth",
                                              code=_lambda.Code.asset("./lambda/lambda_0"))

        lambda_0.add_environment("AUTH_KEY", auth_key)

        # create Lambda 1
        lambda_1 = _lambda.Function(self, "lambda_1",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role1,
                                              timeout = core.Duration.seconds(30),
                                              description = "For HTTP POST/DELETE/CANCEL method, send messages to SQS",
                                              code=_lambda.Code.asset("./lambda/lambda_1"))

        lambda_1.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_1.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_1.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 2
        lambda_2 = _lambda.Function(self, "lambda_2",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role2,
                                              timeout = core.Duration.seconds(30),
                                              description = "For all GET/GET+id method",
                                              code=_lambda.Code.asset("./lambda/lambda_2"))

        lambda_2.add_environment("TABLE_NAME", ddb_table.table_name)

        # create Lambda 3
        lambda_3 = _lambda.Function(self, "lambda_3",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role3,
                                              timeout = core.Duration.seconds(30),
                                              description = "For HTTP POST/DELETE/CANCEL method, receive SQS messages, submit to Batch",
                                              code=_lambda.Code.asset("./lambda/lambda_3"))

        lambda_3.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_3.add_environment("S3_BUCKET", self.bucket.bucket_name)
        lambda_3.add_environment("SQS_QUEUE", queue.queue_url)  
        lambda_3.add_environment("JOB_DEFINITION_NAME", self.job_Definition_name)

        # create sqs invoker
        lambda_3.add_event_source(eventsources.SqsEventSource(queue))

        # create Lambda 4
        lambda_4 = _lambda.Function(self, "lambda_4",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role4,
                                              timeout = core.Duration.seconds(30),
                                              description = "When job succussed, send SNS to user. Triggered by S3",
                                              code=_lambda.Code.asset("./lambda/lambda_4"))

        lambda_4.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_4.add_environment("SNS_ARN", sns_topic.topic_arn)

        # create s3 notification
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(lambda_4),
            s3.NotificationKeyFilter(
                prefix="output/",suffix="tar.gz"
                )
            )

        # create Lambda 5
        self.lambda_5 = _lambda.Function(self, "lambda_5",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role5,
                                              timeout = core.Duration.seconds(30),
                                              description = "When job failed,send SNS to user.Triggered by EventBridge",
                                              code=_lambda.Code.asset("./lambda/lambda_5"))

        self.lambda_5.add_environment("TABLE_NAME", ddb_table.table_name)
        self.lambda_5.add_environment("SNS_ARN", sns_topic.topic_arn)

        # create api-gateway

        apigw_auth = apigatewayv2_authorizers.HttpLambdaAuthorizer(
            authorizer_name = 'apigw_auth',
            response_types = [apigatewayv2_authorizers.HttpLambdaResponseType('SIMPLE')],
            # payload_format_version = apigatewayv2.AuthorizerPayloadVersion('VERSION_2_0'),
            handler = lambda_0
        )

        if len(auth_key)!=0:
            apigw = apigatewayv2.HttpApi(
                self,'apigw',
                api_name = 'af2-apigw',
                default_authorizer = apigw_auth
            )
        else:
            apigw = apigatewayv2.HttpApi(
                self,'apigw',
                api_name = 'af2-apigw',
                # default_authorizer = apigw_auth
            )

        # 不需要显性授权？

        # lambda_1.grant_invoke(apigw)
        # lambda_2.grant_invoke(apigw)
        
        lambda_1_intergation = apigatewayv2_integrations.LambdaProxyIntegration(
            handler = lambda_1
        )
        lambda_2_intergation = apigatewayv2_integrations.LambdaProxyIntegration(
            handler = lambda_2
        )

        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.GET],
            integration = lambda_2_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.GET],
            integration = lambda_2_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.POST],
            integration = lambda_1_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.DELETE],
            integration = lambda_1_intergation
        )
        apigw.add_routes(
            path = '/',
            methods = [apigatewayv2.HttpMethod.ANY],# for CANCEL method
            integration = lambda_1_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.DELETE],
            integration = lambda_1_intergation
        )
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.ANY],# for CANCEL method
            integration = lambda_1_intergation
        )

        core.CfnOutput(
            self,"af2-S3",
            description="S3",
            value=self.bucket.bucket_arn,
        )

        core.CfnOutput(
            self,"af2-APIGW",
            description="APIGW",
            value=apigw.api_endpoint,
        )

        # core.CfnOutput(
        #     self,"af2-SQS",
        #     description="SQS",
        #     value=queue.queue_url,
        # )

        # core.CfnOutput(
        #     self,"af2-DDB",
        #     description="DDB",
        #     value=ddb_table.table_name,
        # )