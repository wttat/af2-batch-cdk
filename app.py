#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

# from af2_batch_cdk.test_stack import TESTCdkStack
from af2_batch_cdk.vpc_ec2 import EC2VPCCdkStack
from af2_batch_cdk.api_gw import APIGWCdkStack
from af2_batch_cdk.batch import BATCHCdkStack
from af2_batch_cdk.nice_dcv import NICEDEVCdkStack


app = core.App()

# test_stack = TESTCdkStack(
#     app,"TESTCdkStack",
# )

### As af2 input/output both in S3, there is no need to put it in a exist VPC.
### Thus, follow setting is recommanded.

use_default_vpc = 0 # set to 0 to do not use the default vpc,set to 1 to use your default VPC in this region,this paramater will overwrite vpcid.
vpc_id = "" # if you wanna to set your own VPC,change this to your vpc'id.

# SSH key pair name, 
key_pair = 'us-east-2' # replace to your own key-pair in the region
mail_address = "wttat8600@gmail.com" # replace your own

# # Set the api-gateway auth_key, it's essential for api gateway in AWS china if you don't have an ICP.
# # auth_key = self.node.try_get_context("auth_key") # replace your own
auth_key = "af2" # replace your own

vpc_stack = EC2VPCCdkStack(app, "EC2VPCCdkStack",
    use_default_vpc = use_default_vpc,
    vpc_id = vpc_id,
    key_pair = key_pair,
    mail_address = mail_address,
    env=core.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
    )
)

api_gw_stack = APIGWCdkStack(app, "APIGWCdkStack",
    vpc = vpc_stack.vpc,
    sns_topic = vpc_stack.sns_topic,
    auth_key = auth_key,
    env=core.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
    )
)

batch_stack = BATCHCdkStack(app,"BATCHCdkStack",
    file_system = vpc_stack.file_system,
    vpc = vpc_stack.vpc,
    sg = vpc_stack.sg,
    repo = vpc_stack.repo,
    bucket = api_gw_stack.bucket,
    key_pair = key_pair,
    lambda_5 = api_gw_stack.lambda_5,
    job_Definition_name = api_gw_stack.job_Definition_name,
    env=core.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"]
    )
)

# nice_dev_stack = NICEDEVCdkStack(app, "NICEDEVCdkStack",
#     key_pair = key_pair,
#     vpc=vpc_stack.vpc,
#     bucket = api_gw_stack.bucket,
#     # pub_subnet = vpc_stack.pub_subnet,
#     env=core.Environment(
#         account=os.environ["CDK_DEFAULT_ACCOUNT"],
#         region=os.environ["CDK_DEFAULT_REGION"]
#     )
# )

app.synth()
