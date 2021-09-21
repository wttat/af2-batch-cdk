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
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_ec2 as ec2

region = os.environ["CDK_DEFAULT_REGION"]

class NICEDEVCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,vpc,bucket,**kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # create EC2 for NICE-DCV
        nice_dcv_ami = ec2.MachineImage.lookup(
            name="Remote Desktop based on NVIDIA GRID and NICE DCV",
            owners=["amazon"]
        )

        ec2_gui = ec2.Instance(self, "ec2_gui",
            instance_type = ec2.InstanceType("g4dn.xlarge"),
            vpc = vpc,
            # vpc_subnets = pub_subnet,
            # security_group = sg,
            machine_image = nice_dcv_ami,
        )
        ec2_gui.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))

        ec2_gui.user_data.add_commands(f"aws s3 cp s3://alphafold2-dataset-bjs/goofys ./ --request-payer --region {region}",
                                        "chmod a+x goofys",
                                        f"./goofys --region {region} {bucket.bucket_name}:output /home/dcv-user/Desktop/s3",
                                        "wget https://pymol.org/installers/PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2",
                                        "tar -jxf PyMOL-2.5.2_293-Linux-x86_64-py37.tar.bz2",
                                        )

        # ./pymol













