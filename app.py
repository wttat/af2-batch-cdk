#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from af2_batch_cdk.test_stack import TESTCdkStack
from af2_batch_cdk.vpc_ec2 import EC2VPCCdkStack
from af2_batch_cdk.api_gw import APIGWCdkStack
from af2_batch_cdk.batch import BATCHCdkStack
from af2_batch_cdk.nice_dcv import NICEDEVCdkStack


app = core.App()

test_stack = TESTCdkStack(
    app,"TESTCdkStack",
)


# SSH key pair name, 
key_pair = 'cn-nw-01' # replace your own in the region
mail_address = "wttat8600@gmail.com" # replace your own

# # Set the api-gateway auth_key, it's essential for api gateway in AWS china if you don't have an ICP.
# # auth_key = self.node.try_get_context("auth_key") # replace your own
# auth_key = "af2" # replace your own

# vpc_stack = EC2VPCCdkStack(app, "EC2VPCCdkStack",
#     key_pair = key_pair,
#     mail_address = mail_address,
#     env=core.Environment(
#     account=os.environ["CDK_DEFAULT_ACCOUNT"],
#     region=os.environ["CDK_DEFAULT_REGION"]
#     )
# )

# api_gw_stack = APIGWCdkStack(app, "APIGWCdkStack",
#     vpc = vpc_stack.vpc,
#     sns_topic = vpc_stack.sns_topic,
#     auth_key = auth_key,
#     env=core.Environment(
#     account=os.environ["CDK_DEFAULT_ACCOUNT"],
#     region=os.environ["CDK_DEFAULT_REGION"]
#     )
# )

# batch_stack = BATCHCdkStack(app,"BATCHCdkStack",
#     file_system = vpc_stack.file_system,
#     vpc=vpc_stack.vpc,
#     repo = vpc_stack.repo,
#     bucket = api_gw_stack.bucket,
#     key_pair = key_pair,
#     lambda_5 = api_gw_stack.lambda_5,
#     env=core.Environment(
#     account=os.environ["CDK_DEFAULT_ACCOUNT"],
#     region=os.environ["CDK_DEFAULT_REGION"]
#     )
# )

# nice_dev_stack = NICEDEVCdkStack(app, "NICEDEVCdkStack",
#     vpc=vpc_stack.vpc,
#     bucket = api_gw_stack.bucket,
#     # pub_subnet = vpc_stack.pub_subnet,
#     env=core.Environment(
#         account=os.environ["CDK_DEFAULT_ACCOUNT"],
#         region=os.environ["CDK_DEFAULT_REGION"]
#     )
# )

app.synth()
