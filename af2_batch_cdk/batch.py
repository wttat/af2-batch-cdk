from constructs import Construct
import os
from aws_cdk import (
    App, Stack,Size,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_ecr as ecr,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_fsx as fsx,
    aws_ecs as ecs,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as eventsources,
    aws_s3_deployment as s3deploy,
    aws_events_targets as targets,
    aws_ecs as ecs
)
from aws_cdk import aws_batch_alpha as batch
import base64

mountPath = "/fsx" # do not touch

input_prefix = "input"
output_prefix = "output"

with open("./user_data/fsx_user_data") as f:
	    user_data_raw = f.read()

region = os.environ["CDK_DEFAULT_REGION"]

class BATCHCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,vpc,sg,file_system,bucket,repo,job_Definition_name, **kwargs) -> None:
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
            block_devices = [ec2.BlockDevice(
                                           device_name="/dev/xvda",
                                           volume=ec2.BlockDeviceVolume.ebs(100,
                                                                            encrypted=True
                                                                            )
                                       )
                            ],
        )

        # create compute env high
        CE_P3_16X = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEP316X",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.P3, ec2.InstanceSize.XLARGE16)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False
        )

        CE_P3_8X = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEP38X",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.P3, ec2.InstanceSize.XLARGE8)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False
        )

        CE_P3_2X = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEP32X",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.P3, ec2.InstanceSize.XLARGE2)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False
        )

        CE_G4DN_2X = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEG4DN2X",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE2)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False
        )

        CE_G4DN_2X_SPOT = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEG4DN2XSPOT",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE2)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False,
            spot=True
        )

        CE_G4DN_12X = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEG4DN12X",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE12)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False
        )

        CE_G4DN_12X_SPOT = batch.ManagedEc2EcsComputeEnvironment(
            self,"Alphafold2CEG4DN12XSPOT",
            vpc=vpc,
            minv_cpus=0,
            instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE12)],
            launch_template=launch_template,
            security_groups=[
                sg,
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            use_optimal_instance_classes=False,
            spot=True
        )

        # CE_G5_2X = batch.ManagedEc2EcsComputeEnvironment(
        #     self,"Alphafold2CEG52X",
        #     vpc=vpc,
        #     minv_cpus=0,
        #     instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G5, ec2.InstanceSize.XLARGE2)],
        #     launch_template=launch_template,
        #     security_groups=[
        #         sg,
        #     ],
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     use_optimal_instance_classes=False
        # )

        # CE_G5_12X = batch.ManagedEc2EcsComputeEnvironment(
        #     self,"Alphafold2CEG512X",
        #     vpc=vpc,
        #     minv_cpus=0,
        #     instance_types=[ec2.InstanceType.of(ec2.InstanceClass.G5, ec2.InstanceSize.XLARGE12)],
        #     launch_template=launch_template,
        #     security_groups=[
        #         sg,
        #     ],
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        #     use_optimal_instance_classes=False
        # )

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
        que_high = batch.JobQueue(self, "Alphafold2JobQueueHigh",
            compute_environments=[{
                "computeEnvironment": CE_P3_16X,
                "order": 1
            }
            ],
            job_queue_name = 'high',
        )

        que_mid = batch.JobQueue(self, "Alphafold2JobQueueMid",
            compute_environments=[{
                "computeEnvironment": CE_P3_8X,
                "order": 1
            }
            ],
            job_queue_name = 'mid',
        )

        que_low = batch.JobQueue(self, "Alphafold2JobQueueLow",
            compute_environments=[
                {
                "computeEnvironment": CE_P3_2X,
                "order": 1
                }
            ],
            job_queue_name = 'low',
        )

        que_g4dn = batch.JobQueue(self, "Alphafold2JobQueueG4dn",
            compute_environments=[
                {
                "computeEnvironment": CE_G4DN_2X,
                "order": 1
                }
            ],
            job_queue_name = 'g4dn',
        )

        que_g4dn_spot = batch.JobQueue(self, "Alphafold2JobQueueG4dnSpot",
            compute_environments=[
                {
                "computeEnvironment": CE_G4DN_2X_SPOT,
                "order": 1
                }
            ],
            job_queue_name = 'g4dn_spot',
        )

        que_g4dn12x = batch.JobQueue(self, "Alphafold2JobQueueG4dn12X",
            compute_environments=[
                {
                "computeEnvironment": CE_G4DN_12X,
                "order": 1
                }
            ],
            job_queue_name = 'g4dn12x',
        )

        que_g4dn12x_spot = batch.JobQueue(self, "Alphafold2JobQueueG4dn12XSpot",
            compute_environments=[
                {
                "computeEnvironment": CE_G4DN_12X_SPOT,
                "order": 1
                }
            ],
            job_queue_name = 'g4dn12x_spot',
        )

        # que_g5 = batch.JobQueue(self, "Alphafold2JobQueueG4dn",
        #     compute_environments=[
        #         {
        #         "computeEnvironment": CE_G5_2X,
        #         "order": 1
        #         }
        #     ],
        #     job_queue_name = 'g5',
        # )

        # que_g512x = batch.JobQueue(self, "Alphafold2JobQueueG4dn12X",
        #     compute_environments=[
        #         {
        #         "computeEnvironment": CE_G5_12X,
        #         "order": 1
        #         }
        #     ],
        #     job_queue_name = 'g512x',
        # )

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
            tag="latest"
        )

        batch_job_role =  iam.Role(
            self,'Alphafold2BatchJobRole',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            description =' IAM role for batch job',
        )
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))
        batch_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        # create job definition
        af2 = batch.EcsJobDefinition(self,"Alphafold2JobDefinition",
            job_definition_name = job_Definition_name,
            container = batch.EcsEc2ContainerDefinition(self,"Alphafold2ContainerDefinition",
                image=image_id,
                job_role=batch_job_role,
                execution_role=batch_job_role,
                command=["/bin/bash","/app/run.sh",
                "-f","Ref::fasta_paths",
                "-t","Ref::max_template_date",
                "-m","Ref::model_preset",
                "-c","Ref::db_preset",
                "-l","Ref::num_multimer_predictions_per_model",
                "-p","Ref::use_precomputed_msas",
                "-r","Ref::models_to_relax",
                "-b","Ref::benchmark",
                ],
                volumes=[batch.EcsVolume.host(
                    name="Alphafold2Lustre",
                    host_path=mountPath,
                    container_path=mountPath
                )],
                environment={
                        "XLA_PYTHON_CLIENT_MEM_FRACTION":"4.0",
                        "TF_FORCE_UNIFIED_MEMORY":"1",
                        "BATCH_BUCKET":bucket.bucket_name,
                        "INPUT_PREFIX":input_prefix,
                        "OUTPUT_PREFIX":output_prefix,
                        "REGION":region,
                },
                user="root",
                cpu=8,
                memory=Size.gibibytes(60),
            ),
            # default parameters
            parameters = {
                "fasta_paths": "fp",
                "max_template_date": "mtd",
                "db_preset":"dp",
                "model_preset":"mp",
                "num_multimer_predictions_per_model":"5",
                "use_precomputed_msas":'false',
                "benchmark":'false',
                "models_to_relax":"best"
            }
        )
            
        
   
