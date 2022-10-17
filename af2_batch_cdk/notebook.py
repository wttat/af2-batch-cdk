import os
from constructs import Construct
from aws_cdk import (
    App, Stack,CfnOutput,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_sagemaker as sagemaker
)

region = os.environ["CDK_DEFAULT_REGION"]

class NOTEBOOKCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,**kwargs):
        super().__init__(scope, construct_id, **kwargs)

        notebook_job_role =  iam.Role(
            self,'Alphafold2NotebookRole',
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
            description =' IAM role for notebook job',
        )
        notebook_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        notebook_job_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess'))

        cfn_notebook_instance = sagemaker.CfnNotebookInstance(self,"Alphafold2Notebook",
            notebook_instance_name="Alphafold2Notebook",
            role_arn=notebook_job_role.role_arn,
            instance_type="ml.t3.medium",
            default_code_repository="https://github.com/wttat/af2-batch-cdk",
            volume_size_in_gb=30,
        )

        
        CfnOutput(
            self,"af2-notebook-name",
            description="af2-notebook",
            value=cfn_notebook_instance.attr_notebook_instance_name,
        )




