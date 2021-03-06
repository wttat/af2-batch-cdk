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
import aws_cdk.aws_events as events
import aws_cdk.aws_sns as sns
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_fsx as fsx
import aws_cdk.aws_apigatewayv2 as apigatewayv2
import aws_cdk.aws_apigatewayv2_authorizers as apigatewayv2_authorizers
import aws_cdk.aws_apigatewayv2_integrations as apigatewayv2_integrations
import aws_cdk.aws_batch as batch

import base64

mountPath = "/fsx" # do not touch

input_prefix = "input"
output_prefix = "output"

with open("./user_data/fsx_user_data") as f:
	    user_data_raw = f.read()

region = os.environ["CDK_DEFAULT_REGION"]

class BATCHCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,vpc,sg,file_system,bucket,repo,key_pair,job_Definition_name, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


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
            self,"Alphafold2BatchInstances",
            launch_template_name="Alphafold2BatchLaunchTemplate",
            user_data = user_data,
            key_name = key_pair,
            block_devices = [ec2.BlockDevice(
                                           device_name="/dev/xvda",
                                           volume=ec2.BlockDeviceVolume.ebs(100,
                                                                            encrypted=True
                                                                            )
                                       )
                            ],
        )

        # create compute env high
        af2_8GPU = batch.ComputeEnvironment(
            self,"Alphafold2CE8GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":0,
                "desiredv_cpus":0,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.16xlarge")],
                "launch_template":{
                    "launch_template_name":"Alphafold2BatchLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    sg,
                ]
            }
        )

        af2_4GPU = batch.ComputeEnvironment(
            self,"Alphafold2CE4GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":0,
                "desiredv_cpus":0,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.8xlarge")],
                "launch_template":{
                    "launch_template_name":"Alphafold2BatchLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    sg,
                            ]
            }
        )

        af2_1GPU = batch.ComputeEnvironment(
            self,"Alphafold2CE1GPU",
            compute_resources = {
                "vpc":vpc,
                "minv_cpus":0,
                "desiredv_cpus":0,
                "maxv_cpus":256,
                "instance_types":[ec2.InstanceType("p3.2xlarge")],
                "launch_template":{
                    "launch_template_name":"Alphafold2BatchLaunchTemplate",
                    "version":"$Latest"
                },
                "security_groups":[
                    sg,
                            ]
                }
        )

        # af2_p4 = batch.ComputeEnvironment(
        #     self,"Alphafold2CEP4",
        #     compute_resources = {
        #         "vpc":vpc,
        #         "minv_cpus":0,
        #         "desiredv_cpus":0,
        #         "maxv_cpus":256,
        #         "instance_types":[ec2.InstanceType("p4d.24xlarge")],
        #         "launch_template":{
        #             "launch_template_name":"Alphafold2BatchLaunchTemplate",
        #             "version":"$Latest"
        #         },
        #         "security_groups":[
        #             sg,
        #                     ]
        #         }
        # )
        
        # create job queue
        af_high = batch.JobQueue(self, "Alphafold2JobQueueHigh",
            compute_environments=[{
                "computeEnvironment": af2_8GPU,
                "order": 1
            }
            ],
            job_queue_name = 'high',
        )

        af_mid = batch.JobQueue(self, "Alphafold2JobQueueMid",
            compute_environments=[{
                "computeEnvironment": af2_4GPU,
                "order": 1
            }
            ],
            job_queue_name = 'mid',
        )

        af_low = batch.JobQueue(self, "Alphafold2JobQueueLow",
            compute_environments=[
                {
                "computeEnvironment": af2_1GPU,
                "order": 1
                }
            ],
            job_queue_name = 'low',
        )

        # af_p4 = batch.JobQueue(self, "JobQueue_P4",
        #     compute_environments=[{
        #         "computeEnvironment": af2_p4,
        #         "order": 1
        #     }
        #     ],
        #     job_queue_name = 'p4',
        # )

        image_id = ecs.ContainerImage.from_ecr_repository(
            repository=ecr.Repository.from_repository_name(self, "GetCompRegRepoName",repo.repository_name),
            tag="lastest"
        )

        batch_job_role =  iam.Role(
            self,'Alphafold2BatchJobRole',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            description =' IAM role for batch job',
        )
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))

        # create job definition
        af2 = batch.JobDefinition(self,"Alphafold2JobDefinition",
            job_definition_name = job_Definition_name,
            container = {
                "image": image_id,
                "job_role" : batch_job_role,
                "command":["/bin/bash","/app/run.sh",
                "-f","Ref::fasta_paths",
                "-t","Ref::max_template_date",
                "-m","Ref::model_preset",
                "-c","Ref::db_preset",
                "-l","Ref::num_multimer_predictions_per_model",
                "-p","Ref::use_precomputed_msas",
                "-r","Ref::run_relax",
                "-b","Ref::benchmark",
                ],
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
                        "INPUT_PREFIX":input_prefix,
                        "OUTPUT_PREFIX":output_prefix,
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
                "memory_limit_mib":60000,
                "log_configuration":{
                    "log_driver":batch.LogDriver.AWSLOGS
                }
            },
            
            # default parameters
            parameters = {
                "fasta_paths": "fp",
                "max_template_date": "mtd",
                "db_preset":"dp",
                "model_preset":"mp",
                "num_multimer_predictions_per_model":"5",
                "use_precomputed_msas":'false',
                "benchmark":'false',
                "run_relax":"true"
            },
            
        )
   
