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
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_sagemaker as sagemaker

region = os.environ["CDK_DEFAULT_REGION"]

class NOTEBOOKCdkStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,**kwargs):
        super().__init__(scope, construct_id, **kwargs)

        notebook_job_role =  iam.Role(
            self,'Alphafold2NotebookRole',
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
            description =' IAM role for notebook job',
        )
        notebook_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        notebook_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess'))

        cfn_notebook_instance = sagemaker.CfnNotebookInstance(self,"Alphafold2Notebook",
            notebook_instance_name="alphafold2-notebook",
            role_arn=notebook_job_role.role_arn,
            instance_type="ml.t2.medium",
            default_code_repository="https://github.com/wttat/af2-batch-cdk",
            volume_size_in_gb=30,
        )

        
        core.CfnOutput(
            self,"af2-notebook-name",
            description="af2-notebook",
            value=self.cfn_notebook_instance.attr_notebook_instance_name,
        )




