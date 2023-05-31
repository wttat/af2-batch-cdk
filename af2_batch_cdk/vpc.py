# from typing import Protocol
import os
from constructs import Construct
from aws_cdk import (
    App, Stack,RemovalPolicy,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_fsx as fsx,
    aws_sns as sns
   
)

import base64

# cdk deploy -c key_pair=cn-nw-01 dataset_upload_s3=True

# key_pair = self.node.try_get_context("key_pair") # replace your own in the region

mountPath = "/fsx" # do not touch

# get account ID and region
account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

if region == 'cn-north-1' or region == 'cn-northwest-1':
    image_arn='s3://alphafold2-raw-data/prod/images/af2-batch6.tar'
    dataset_arn='s3://alphafold2-raw-data/prod/datasets/dataset5.tar.gz'
    dataset_region='cn-northwest-1'
else:
    image_arn='s3://alphafold2/prod/images/af2-batch6.tar'
    dataset_arn='s3://alphafold2/prod/datasets/dataset5.tar.gz'
    dataset_region='us-east-1'

# af2-batch image file name
image_name=image_arn.split("/")[-1]

# dataset name
dataset_name=dataset_arn.split("/")[-1]

with open("./user_data/tmpec2_user_data") as f:
	    user_data_raw = f.read()

class VPCCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, key_pair,sns_mail,vpc_id,use_default_vpc,**kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #  create a SNS topic   
        self.sns_topic = sns.Topic(
            self, "Alphafold2SnsTopic-",
            display_name="Alphafold2 Notification",
        )

        sns.Subscription(
            self,"Alphafold2SnsSubscription",
            topic=self.sns_topic,
            endpoint=sns_mail,
            protocol=sns.SubscriptionProtocol.EMAIL,
        )

        # create ECR repo
        self.repo = ecr.Repository(
            self,'Alphafold2EcrRepo-',
            removal_policy=RemovalPolicy.DESTROY
        )

        # choose or create a vpc
        if use_default_vpc:
            self.vpc = ec2.Vpc.from_lookup(self, 'Alphafold2VPC', is_default = True) 
        elif len(vpc_id)!=0:
            self.vpc = ec2.Vpc.from_lookup(self, 'Alphafold2VPC',vpc_id = vpc_id) 
        else:
            self.vpc = ec2.Vpc(self, "Alphafold2VPC",
            max_azs=99, # use all az in this region
            nat_gateways=1,
            subnet_configuration=[
                {"name":"public","subnetType":ec2.SubnetType.PUBLIC},
                {"name":"private","subnetType":ec2.SubnetType.PRIVATE_WITH_EGRESS}
                ]
            )

        self.sg = ec2.SecurityGroup(self, "Alphafold2SecurityGroup",
                                vpc=self.vpc,
                                description="Allow access from VPC CIDR and SSH",
                                security_group_name="CDK SecurityGroup",
                                allow_all_outbound=True,
                            )
        self.sg.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block),ec2.Port.all_traffic())
        self.sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow ssh access from the world")

        self.file_system = fsx.LustreFileSystem(
            self,'Alphafold2FileSystem',
            lustre_configuration={"deployment_type": fsx.LustreDeploymentType.SCRATCH_2,"data_compression_type": fsx.LustreDataCompressionType.LZ4},
            # lustre_configuration={"deployment_type": fsx.LustreDeploymentType.SCRATCH_2,"data_compression_type": fsx.LustreDataCompressionType.NONE},
            vpc = self.vpc,
            vpc_subnet=self.vpc.private_subnets[0],
            storage_capacity_gib = 2400,
            # storage_capacity_gib = 4800,
            removal_policy=RemovalPolicy.DESTROY,
            security_group = self.sg,
        )

        amzn_linux = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                                                              edition=ec2.AmazonLinuxEdition.STANDARD,
                                                              virtualization=ec2.AmazonLinuxVirt.HVM,
                                                              storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE)

        dnsName = self.file_system.dns_name
        mountName = self.file_system.mount_name
        fileSystemId = self.file_system.file_system_id

        if region == "cn-north-1" or region == "cn-northwest-1":
            ecr_endpoint = account+'.dkr.ecr.'+region+'.amazonaws.com.cn'
        else:
            ecr_endpoint = account+'.dkr.ecr.'+region+'.amazonaws.com'


        # create EC2 for dataset.tar.gz download & ECR image upload & dataset upload
        ec2_tmp = ec2.Instance(self, "Alphafold2DatasetDownload",
            instance_type = ec2.InstanceType("c5.9xlarge"),
            vpc = self.vpc,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            machine_image = amzn_linux,
            key_name = key_pair,
            block_devices = [ec2.BlockDevice(
                                           device_name="/dev/xvda",
                                           volume=ec2.BlockDeviceVolume.ebs(50,
                                                                            encrypted=True
                                                                            )
                                       )
                            ],
        )
        ec2_tmp.add_security_group(self.sg)

        self.file_system.connections.allow_default_port_from(ec2_tmp)

        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"))
        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryFullAccess"))
        ec2_tmp.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSNSFullAccess"))

        ec2_tmp.user_data.add_commands("set -eux",
                                        "yum update -y",
                                        "yum install pigz -y",
                                        "amazon-linux-extras install docker -y",
                                        "amazon-linux-extras install -y lustre2.10",
                                        "service docker start",
                                        "chmod 666 /var/run/docker.sock",
                                        f"mkdir -p {mountPath}",
                                        f"chmod 777 {mountPath}", 
                                        f"chown ec2-user:ec2-user {mountPath}",
                                        # Maybe bugs in fsx.dnsName, 
                                        # extra .cn hostname in AWS china region. Current date:09/11/2021
                                        # f"mount -t lustre -o noatime,flock {dnsName}@tcp:/{mountName} {mountPath}",
                                        f"mount -t lustre -o noatime,flock {fileSystemId}.fsx.{region}.amazonaws.com@tcp:/{mountName} {mountPath}",
                                        f"cd {mountPath}",
                                        f"aws s3 cp {image_arn} ./ --request-payer --region {dataset_region}",
                                        f"docker load < {image_name}",
                                        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {ecr_endpoint}",
                                        f"docker tag $(docker images -q) {self.repo.repository_uri_for_tag('latest')}",
                                        f"docker push {self.repo.repository_uri_for_tag('latest')}",
                                        f"aws s3 cp {dataset_arn} ./ --request-payer --region {dataset_region}",
                                        f"tar -I pigz -xvf {dataset_name} --directory={mountPath}"
                                        )

        ec2_tmp.user_data.add_on_exit_commands(
            f"aws sns publish --message 'You could check the fsx volume and start training, then manully terminated the EC2.' --topic-arn {self.sns_topic.topic_arn} --subject 'Your dataset have perpared.' --region {region}"
        )
