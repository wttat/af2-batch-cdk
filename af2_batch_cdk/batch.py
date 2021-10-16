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
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_events as events
import aws_cdk.aws_sns as sns
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_fsx as fsx
import aws_cdk.aws_apigatewayv2 as apigatewayv2
import aws_cdk.aws_apigatewayv2_authorizers as apigatewayv2_authorizers
import aws_cdk.aws_apigatewayv2_integrations as apigatewayv2_integrations
import aws_cdk.aws_s3_notifications as s3n
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_batch as batch

import base64

mountPath = "/fsx" # do not touch

with open("./user_data/fsx_user_data") as f:
	    user_data_raw = f.read()

# get account ID and region
# account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

class BATCHCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,vpc,sg,file_system,bucket,repo,key_pair,lambda_5,job_Definition_name, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        failed_rule = events.Rule(
            self,"FAILEDSNS",
            description = "for failed batch job",
            event_pattern = events.EventPattern(
                source = ["aws.batch"],
                detail = {
                    "status": [
                        "FAILED"
                        ]
                    },
                detail_type = ["Batch Job State Change"],
            )
        )

        failed_rule.add_target(
            targets.LambdaFunction(
                lambda_5,
                max_event_age=cdk.Duration.hours(2), # Otional: set the maxEventAge retry policy
                retry_attempts=2
            )
        )

        dnsName = file_system.dns_name
        mountName = file_system.mount_name
        fileSystemId = file_system.file_system_id

        user_data = ec2.MultipartUserData()
        user_data.add_part(
            ec2.MultipartBody.from_user_data(
                ec2.UserData.custom(
                    "amazon-linux-extras install -y lustre2.10\n"
                    f"mkdir -p {mountPath}\n"
                    # Maybe bugs in fsx.dnsName, 
                    # extra .cn hostname in AWS china region. Current date:09/11/2021
                    # f"mount -t lustre -o noatime,flock {dnsName}@tcp:/{mountName} {mountPath}",
                    f"mount -t lustre -o noatime,flock {fileSystemId}.fsx.{region}.amazonaws.com@tcp:/{mountName} {mountPath}\n"
                    f"echo '{fileSystemId}.fsx.{region}.amazonaws.com@tcp:/{mountName} {mountPath} lustre defaults,noatime,flock,_netdev 0 0' >> /etc/fstab \n"
                    "mkdir -p /tmp/alphafold"
                    )
                ),
            )

        launch_template = ec2.LaunchTemplate(
            self,"AF2Instances",
            launch_template_name="lustreLaunchTemplate",
            user_data = user_data,
            key_name = key_pair, # maybe should not be allowed after debug
            # user_data = ec2.UserData.custom(user_data)
        )

        # create compute env high
        af2_8GPU = batch.ComputeEnvironment(
            self,"ComputeEnvironment_8GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":0,
                "desiredv_cpus":0,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.16xlarge")],
                "launch_template":{
                    # "launch_template_name":launch_template.launch_template_name,
                    "launch_template_name":"lustreLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    # ec2.SecurityGroup.from_security_group_id(
                    #             self,"AF28GPUSG",
                    #             security_group_id=vpc.vpc_default_security_group
                    #         )
                    sg,
                ]
            }
        )

        af2_4GPU = batch.ComputeEnvironment(
            self,"ComputeEnvironment_4GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":0,
                "desiredv_cpus":0,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.8xlarge")],
                "launch_template":{
                    "launch_template_name":"lustreLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    # ec2.SecurityGroup.from_security_group_id(
                    #             self,"AF24GPUSG",
                    #             security_group_id=vpc.vpc_default_security_group
                    #         )
                    sg,
                            ]
            }
        )

        af2_1GPU = batch.ComputeEnvironment(
            self,"ComputeEnvironment_1GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":8,
                "desiredv_cpus":8,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.2xlarge")],
                "launch_template":{
                    "launch_template_name":"lustreLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    # ec2.SecurityGroup.from_security_group_id(
                    #             self,"AF21GPUSG",
                    #             security_group_id=vpc.vpc_default_security_group
                    #         )
                    sg,
                            ]
                }
        )

        # create job queue
        af_high = batch.JobQueue(self, "JobQueue_High",
            compute_environments=[{
                # Defines a collection of compute resources to handle assigned batch jobs
                "computeEnvironment": af2_8GPU,
                # Order determines the allocation order for jobs (i.e. Lower means higher preference for job assignment)
                "order": 1
            }
            ],
            job_queue_name = 'high',
        )

        af_mid = batch.JobQueue(self, "JobQueue_Mid",
            compute_environments=[{
                # Defines a collection of compute resources to handle assigned batch jobs
                "computeEnvironment": af2_4GPU,
                # Order determines the allocation order for jobs (i.e. Lower means higher preference for job assignment)
                "order": 1
            }
            ],
            job_queue_name = 'mid',
        )

        af_low = batch.JobQueue(self, "JobQueue_Low",
            compute_environments=[{
                # Defines a collection of compute resources to handle assigned batch jobs
                "computeEnvironment": af2_1GPU,
                # Order determines the allocation order for jobs (i.e. Lower means higher preference for job assignment)
                "order": 1
            }
            ],
            job_queue_name = 'low',
        )

        image_id = ecs.ContainerImage.from_ecr_repository(
            repository=ecr.Repository.from_repository_name(self, "GetCompRegRepoName",repo.repository_name),
            tag="lastest"
        )

        batch_job_role =  iam.Role(
            self,'batch job role',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            description =' IAM role for batch job',
        )
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonFSxReadOnlyAccess'))

        # create job definition
        af2 = batch.JobDefinition(self,"JobDefinition",
            job_definition_name = job_Definition_name,
            container = {
                # "image": repo.repository_uri_for_tag("lastest"),
                "image": image_id,
                "job_role" : batch_job_role,
                "command":["/bin/bash","/app/run.sh","-f","Ref::fasta_paths","-m","Ref::model_names","-d","Ref::max_template_date","-p","Ref::preset"],
                "volumes": [
                    {
                        "host":{
                            "sourcePath":mountPath,
                        },
                        "name":"Lustre"
                    }
                ],
                "environment":{
                        "XLA_PYTHON_CLIENT_MEM_FRACTION":"4.0",
                        "TF_FORCE_UNIFIED_MEMORY":"1",
                        "BATCH_BUCKET":bucket.bucket_name,
                        "BATCH_DIR_PREFIX":"input",
                        "REGION":region,
                },
                "mount_points":[
                    {
                        "containerPath": mountPath,
                        "readOnly":False,
                        "sourceVolume": "Lustre",
                    }
                ],
                "user":"root",
                "gpu_count":1,
                "vcpus":8,
                "memory_limit_mib":48000,
                "log_configuration":{
                    "log_driver":batch.LogDriver.AWSLOGS
                }
            },

            parameters = {
                # default parameters
                "model_names": "mn",
                "max_template_date": "mtd",
                "preset": "p",
                "fasta_paths": "fp"
            },
            
        )
   
