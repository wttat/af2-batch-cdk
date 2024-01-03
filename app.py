#!/usr/bin/env python3
import os

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import  App, Stack, Tags,Environment

# from af2_batch_cdk.test_stack import TESTCdkStack
from af2_batch_cdk.vpc import VPCCdkStack
from af2_batch_cdk.api_gw import APIGWCdkStack
from af2_batch_cdk.batch import BATCHCdkStack
from af2_batch_cdk.notebook import NOTEBOOKCdkStack
from af2_batch_cdk.nice_dcv import NICEDEVCdkStack

app = App()

use_default_vpc = 0 # set to 0 to do not use the default vpc,set to 1 to use your default VPC in this region,this paramater will overwrite vpcid.
vpc_id = "" # if you wanna to set your own VPC,change this to your vpc'id.

# SSH key pair name, 
key_pair = os.environ["KEYPAIR"]
sns_mail = os.environ["MAIL"]
auth_key = os.environ["AUTH"]

Tag = "Alphafold2_v2.3.2_03"

vpc_stack = VPCCdkStack(app, "VPCCdkStack",
    use_default_vpc = use_default_vpc,
    vpc_id = vpc_id,
    key_pair = key_pair,
    sns_mail = sns_mail,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    )
)

api_gw_stack = APIGWCdkStack(app, "APIGWCdkStack",
    sns_topic = vpc_stack.sns_topic,
    auth_key = auth_key,
    tag = Tag,
    env=Environment(
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
    job_Definition_name = api_gw_stack.job_Definition_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    )
)

notebook_stack = NOTEBOOKCdkStack(app,"NOTEBOOKCdkStack",
    )



Tags.of(vpc_stack).add("AWS-GCR-HCLS-Solutions", Tag)
Tags.of(api_gw_stack).add("AWS-GCR-HCLS-Solutions", Tag)
Tags.of(batch_stack).add("AWS-GCR-HCLS-Solutions", Tag)
Tags.of(notebook_stack).add("AWS-GCR-HCLS-Solutions", Tag)

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
