from typing import Protocol
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
import aws_cdk.aws_sns as sns
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_fsx as fsx
import aws_cdk.apigatewayv2 as apigatewayv2
import aws_cdk.apigatewayv2_authorizers as apigatewayv2_authorizers
import aws_cdk.apigatewayv2_integrations as apigatewayv2_integrations
import aws_cdk.aws_s3_notifications as s3n


# Set the api-gateway auth_key, it's essential for api gateway in AWS china if you don't have an ICP.
auth_key = 'af2'

# Set the mail address for SNS
mail_address = 'wttat8600@gmail.com'

# Set whether to upload the entire dataset to S3 for backup.
dataset_upload_s3 = True

# dataset arn
dataset_arn='s3://alphafold2-raw-data/dataset.tar.gz'

# dataset region
dataset_region='cn-north-1'

# af2-batch image arn
image_arn='s3://alphafold2-raw-data/af2-batch.tar'

mountPath = "/fsx"

# get account ID and region
account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

class Af2BatchCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create dynamodb table
        ddb_table = dynamodb.Table(
            self,'af2_ddb',
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            )
        )

        # create ECR repo
        repo = ecr.Repository(
            self,'af2',
        )

        # create a s3 bucket
        bucket = s3.Bucket(
            self,"af2_bucket",
        )

        #  create a SNS topic   
        sns_topic = sns.Topic(
            self, "Topic",
            display_name="Customer subscription topic"
        )

        sns.Subscription(
            self,"Subscription",
            topic=sns_topic,
            endpoint=mail_address,
            protocol=sns.SubscriptionProtocol.EMAIL
        )

        #  create a SQS queue
        queue = sqs.Queue(self, "SQSQueue")

        # create fsx for lustre, if we use 2.4T storage, then must apply LZ4 compression

        file_system = fsx.LustreFileSystem(
            self,'fsx',
            fsx.LustreConfiguration(fsx.LustreDeploymentType('PERSISTENT_1'),
                                        per_unit_storage_throughput=200),
            # vpc = 
            # vpc_subnet = 
            storage_capacity_gib = 2400,
        )

        dnsName = file_system.dns_name
        mountName = file_system.mount_name

        # create EC2 for dataset.tar.gz download & ECR image upload & dataset upload
        ec2_tmp = ec2.Instance(self, "ec2_tmp",
            instance_type=ec2.InstanceType("c5.9xlarge"),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
        )

        # connect to fsx
        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonFSxFullAccess"))
        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"))
        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryFullAccess"))
        fsx.connections.allow_default_port_from(ec2_tmp)

        # add ec2_tmp user data 
        ec2_tmp.user_data.add_commands("set -eux",
                                        "yum update -y",
                                        "yum install pigz -y",
                                        "amazon-linux-extras install -y lustre2.10", 
                                        f"mkdir -p {mountPath}",
                                        f"chmod 777 {mountPath}", 
                                        f"chown ec2-user:ec2-user {mountPath}",
                                        f"mount -t lustre -o noatime,flock {dnsName}@tcp:/{mountName} {mountPath}",
                                        f"cd {mountPath}",
                                        f"aws s3 cp {dataset_arn} ./ --request-payer --region {dataset_region}",
                                        f"tar -I pigz -xvf dataset.tar.gz --directory={mountPath}",
                                        "rm -rf dataset.tar.gz",
                                        f"aws s3 cp {image_arn} ./ --request-payer",
                                        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {repo.repository_uri()}",
                                        )

        # create EC2 for GUI, AMI : NICE-DCV

        ec2_gui = ec2.Instance(self, "ec2_gui"
        )
        ec2_gui.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))

        # sudo yum install awscli
        # aws configure
        # aws s3 cp s3://alphafold2-dataset-bjs/goofys ./ --request-payer
        # chmod a+x goofys
        # ./goofys --region cn-north-1 af2-batch:output /home/dcv-user/Desktop/s3
        # wget https://pymol.org/installers/PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2
        # tar -jxf PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2
        # ./pymol

        # create IAM role 0
        role0 = iam.Role(
            self,'role_0',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_0',
        )

        role0.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))

        # create IAM role 1
        role1 = iam.Role(
            self,'role_1',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_1',
        )

        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role1.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role 2
        role2 = iam.Role(
            self,'role_2',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_2',
        )

        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsReadOnlyAccess'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'))
        role2.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSBatchFullAccess'))

        # create IAM role 3
        role3 = iam.Role(
            self,'role_3',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_3',
        )

        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
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

        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        role4.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSFullAccess'))
        role3.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'))

        # create IAM role 5
        role5 = iam.Role(
            self,'role_5',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description =' IAM role for lambda_5',
        )

        role5.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSLambdaBasicExecutionRole'))
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
                                              description = "For HTTP POST/DELETE/CANCEL method, send messages to SQS",
                                              code=_lambda.Code.asset("./lambda/lambda_1"))

        lambda_1.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_1.add_environment("S3_BUCKET", bucket.bucket_name)
        lambda_1.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 2
        lambda_2 = _lambda.Function(self, "lambda_2",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role2,
                                              description = "For all GET/GET+id method",
                                              code=_lambda.Code.asset("./lambda/lambda_2"))

        lambda_2.add_environment("TABLE_NAME", ddb_table.table_name)

        # create Lambda 3
        lambda_3 = _lambda.Function(self, "lambda_3",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role3,
                                              description = "For HTTP POST/DELETE/CANCEL method, receive SQS messages, submit to Batch",
                                              code=_lambda.Code.asset("./lambda/lambda_3"))

        lambda_3.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_3.add_environment("S3_BUCKET", bucket.bucket_name)
        lambda_3.add_environment("SQS_QUEUE", queue.queue_url)

        # create Lambda 4
        lambda_4 = _lambda.Function(self, "lambda_4",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role4,
                                              description = "When job succussed, send SNS to user. Triggered by S3",
                                              code=_lambda.Code.asset("./lambda/lambda_4"))

        lambda_4.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_4.add_environment("SNS_ARN", sns_topic.topic_arn)

        # create s3 notification
        bucket.add_event_notification(s3.EventType.OBJECT_CREATED,s3n.LambdaDestination(lambda_4),s3.NotificationKeyFilter(prefix="output/",suffix="tar.gz"))

        # create Lambda 5
        lambda_5 = _lambda.Function(self, "lambda_5",
                                              runtime=_lambda.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              role = role5,
                                              description = "When job failed,send SNS to user.Triggered by EventBridge",
                                              code=_lambda.Code.asset("./lambda/lambda_5"))

        lambda_5.add_environment("TABLE_NAME", ddb_table.table_name)
        lambda_5.add_environment("SNS_ARN", sns_topic.topic_arn)

        # create api-gateway

        apigw_auth = apigatewayv2_authorizers.HttpLambdaAuthorizer(
            authorizer_name = 'apigw_auth',
            handler = lambda_0
        )

        apigw = apigatewayv2.HttpApi(
            self,'apigw',
            api_name = 'af2-apigw',
            default_authorizer = apigw_auth
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
            path = '/',
            methods = [apigatewayv2.HttpMethod.POST],
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
        apigw.add_routes(
            path = '/{id}',
            methods = [apigatewayv2.HttpMethod.GET],
            integration = lambda_2_intergation
        )

        # create batch 


    












