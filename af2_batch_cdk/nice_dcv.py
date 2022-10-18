import os
from constructs import Construct
from aws_cdk import (
    App, Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2
)

region = os.environ["CDK_DEFAULT_REGION"]

class NICEDEVCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,key_pair,vpc,bucket,**kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # create EC2 for NICE-DCV
        # nice_dcv_ami = ec2.MachineImage.lookup(
        #     name="DCV-AmazonLinux2*NVIDIA*",
        #     # name="Remote Desktop based on NVIDIA GRID and NICE DCV",
        #     # owners=["amazon"]
        # )
        sg_dcv = ec2.SecurityGroup(self, "nicedcvSG",
                                vpc=vpc,
                                description="for nice dcv and ssh from anywhere",
                                security_group_name="CDK SecurityGroup for nice dcv ssh",
                                allow_all_outbound=True,
                            )
        sg_dcv.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow ssh access from the world")
        sg_dcv.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8443), "allow nice dcv access from the world")

        ec2_gui = ec2.Instance(self, "ec2_gui",
            instance_type = ec2.InstanceType("g4dn.xlarge"),
            vpc = vpc,
            key_name = key_pair,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group = sg_dcv,
            machine_image = ec2.GenericLinuxImage({
                'cn-north-1':'ami-03e41aa4baa635f04',
                'cn-northwest-1':'ami-09cf9c90783446a1e'
            }
            )
        )
        ec2_gui.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))

        ec2_gui.user_data.add_commands(f"wget https://github.com/kahing/goofys/releases/latest/download/goofys",
                                        "chmod a+x goofys",
                                        "mkdir /home/dcv-user/Desktop/s3",
                                        f"./goofys --region {region} {bucket.bucket_name}:output /home/dcv-user/Desktop/s3",
                                        "wget https://pymol.org/installers/PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2",
                                        "tar -jxf PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2",
                                        )