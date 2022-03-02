
# Alphafold2 on AWS deploy guide:

AWS Blog：https://aws.amazon.com/cn/blogs/china/one-click-construction-of-a-highly-available-protein-structure-prediction-platform-on-the-cloud-part-one/

Architecture diagram on AWS：
![avatar](architecture.png)

## Modified Alphafold2 source code GitHub Repo：

https://github.com/wttat/alphafold

## For IAM policy when deployed please check policy.json

## Deployed steps. Based on Amazon Linux 2 AMI

1. Install Node and Npm.
```
wget https://nodejs.org/dist/v14.18.1/node-v14.18.1-linux-x64.tar.xz
tar xvf node-v14.18.1-linux-x64.tar.xz
sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/node /usr/local/bin
sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/npm /usr/local/bin
```
2. Set PATH env.
```
export PATH=$PATH:$(npm get prefix)/bin
```
3. Install Git.
```
sudo yum install -y git
```
4. Clone Repo.
```
git clone https://github.com/wttat/af2-batch-cdk
cd af2-batch-cdk
```
1. Install dependancy
```
pip3 install -r requirements.txt
```
& if in China 
```
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
6. Install CDK@v1
```
npm install -g aws-cdk@1.144.0
```
7. Modify app.py (**Required**) and af2_batch_cdk/batch.py, check details below. 
8. If never run cdk before in this region, use below code to init, do change the ACCOUNT_ID and REGION:
```
cdk bootstrap aws://{ACCOUNT_ID}/{REGION}
```
9. Generate Cloudformation template
```
cdk synth
```
10. Deploy all stacks.
```
cdk deploy --all
```
11. Confirm the SNS email to receive follow-up notification.
12. There will be an c5.9xlarge EC2 launched to download all dataset and images and save to Fsx for lustre. After everything prepared(about 3h), you will received a email notification, you could terminate the EC2 and begin to submit alphafold2 job2 via API.
13. Modify the command.json, check details below. 

## Manually Settings

1. app.py. (Change to set by env instead of editing file later)
    
    - Line 23/24. VPC settings:
      - Create a new vpc(Highly recommended): 
      ```
      use_default_vpc=0
      vpc_id=""
      ```
      - Use default vpc:
      ```
      use_default_vpc=1
      vpc_id=""
      ```

      - Use a new vpc:
      ```
      use_default_vpc=0
      vpc_id="{vpc_id}"
      ```

      Note: if you set use_default_vpc=1 and vpc_id at the same time, use_default_vpc will override vpc_id and use default vpc.

    - Line 27. Key pair setting:

      ```
      key_pair = '{key_pair}'
      ```

    - Line 28. SNS email setting:

        ```
        mail_address = "{mail_address}"
        ```

    - Line 32. API GW Authentication key.:
        ```
        auth_key = "{auth_key}"
        ```
    - Line 75-84. Nice DCV instance(Only tested in AWS China region).
        
        Uncomment to use Nice DCV to visualize output pdb files.
2. af2_batch_cdk/batch.py
   - Line 184-205. Uncomment to use P4 batch CE.
   - Line 241-250. Uncomment to use P4 batch que.
      
      Note: You have to do this in the same time.

## Parameter Description of command.json 

For Job Settings:
1. fasta.type:string,**Required**:
    
    The name of protein to be predicted.
2. file_name.type:string,**Required**:
    
    The name of fasta file which stored in S3's input folder.

3. que.type:string.options:*{low/mid/high/p4}*,**Required**:
   
   The GPU instance to use,which indicated for [p3.2xlarge、p3.8xlarge,p3.16xlarge and p4d.24xlarge].p4 needs manually uncomment。
4. comment.type:string

    The comment for this job。
5. gpu.type:int.Default:[1]:
   
   The number of GPU to use.When using p3 instances，each gpu means 8vcpu，60G mem,when using p4 instance，each gpu means 12vcpu，160G mem.

   If the fasta contains over 1000aa, one V100 is not enough.
   But it's a waste to use too many gpus, because the jax cant really take advantage of multi-gpu.

For Alphfold2 Settings:
1. db_preset.type:string.options:*{reduced_dbs/full_dbs}*,Default:full_dbs 
    
    reduced_dbs: This preset is optimized for speed and lower hardware requirements. It runs with a reduced version of the BFD database. It requires 8 CPU cores (vCPUs), 8 GB of RAM, and 600 GB of disk space.
    
    full_dbs: This runs with all genetic databases used at CASP14.
2. model_preset.type:string.options:*{monomer/monomer_casp14/monomer_ptm/multimer}* **Required**:
   
   monomer:This is the original model used at CASP14 with no ensembling.
   
   monomer_casp14: This is the original model used at CASP14 with num_ensemble=8, matching our CASP14 configuration. This is largely provided for reproducibility as it is 8x more computationally expensive for limited accuracy gain (+0.1 average GDT gain on CASP14 domains).
   
   monomer_ptm: This is the original CASP14 model fine tuned with the pTM head, providing a pairwise confidence measure. It is slightly less accurate than the normal monomer model.
   
   multimer: This is the AlphaFold-Multimer (https://github.com/deepmind/alphafold#citing-this-work) model. To use this model, provide a multi-sequence FASTA file. In addition, the UniProt database should have been downloaded.
3. run_relax.type:string(bool).options:*{true/false}*,Default:true
   
   Whether to run the final relaxation step on the predicted models. Turning relax off might result in predictions with distracting stereochemical violations but might help in case you are having issues with the relaxation stage.
4. is_prokaryote_list.type:string(bool).options:[true/false].Default:[false]

    Determine whether all input sequences in the given fasta file are prokaryotic. If that is not the case or the origin is unknown, set to false for that fasta.

5. max_template_date.type:string(YYYY-MM-DD),Default:[2021-11-01]: 
    
    If you are predicting the structure of a protein that is already in PDB and you wish to avoid using it as a template, then max_template_date must be set to be before the release date of the structure

  

## API for Alphafold2

* Upload the fasta file to the input folder in the S3 bucket just created. Check the S3 bucket arn in the cdk output.
* Check the API Gateway's URL in the cdk output or via AWS console.  
* Using Postman to do this more convenient.
1. POST:Submit a job using POST method,change the KEY(if set) and ApiGW_URL to your own. 

```
curl -X "POST" -H "Authorization: {KEY}" -H "Content-Type: application/json" {ApiGW_URL} -d @command.json
```

2. GET ALL:Query all jobs, change the KEY(if set) and ApiGW_URL to your own:

```
curl -H "Authorization: {KEY}" -H {ApiGW_URL}
```

3. GET ONE:Query one job, change the KEY(if set) and ApiGW_URL to your own,the id of job could be searched via  GET ALL or POST:

```
curl -H "Authorization: {KEY}" -H {ApiGW_URL}/{id}
```

4. CANCEL ALL:Cancel all running jobs,change the KEY(if set) and ApiGW_URL to your own. 

```
curl -X "CANCEL" -H "Authorization: {KEY}"  {ApiGW_URL}
```

5. CANCEL ONE:Cancel running job,change the KEY(if set) and ApiGW_URL to your own,the id of job could be searched via  GET ALL or POST: 

```
curl -X "CANCEL" -H "Authorization: {KEY}"  {ApiGW_URL}/{id}
```
6. DELETE ALL:Delete all finished or failed jobs,change the KEY(if set) and ApiGW_URL to your own. 

```
curl -X "DELETE" -H "Authorization: {KEY}"  {ApiGW_URL}
```

1. DELETE ONE:DELETE finished or failed job,change the KEY(if set) and ApiGW_URL to your own,the id of job could be searched via GET ALL or POST: 

```
curl -X "DELETE" -H "Authorization: {KEY}"  {ApiGW_URL}/{id}
```
Enjoy!



## Total cost calculate：
* The cost filed in DynamoDB counts the number of seconds each task runs. 
* Use tag {AWS-GCR-HLCS-Solutions:Alphafold2} to track total cost. Check:https://docs.aws.amazon.com/zh_cn/awsaccountbilling/latest/aboutv2/activating-tags.html

## Current dataset version：

1. dataset3.tar.gz
    
    update params to alphafold_params_2022-01-19.tar.
2. dataset2.tar.gz
    
    update the dataset and params used by multimer.
3. dataset.tar.gz

    original version.

## Changelog

### 02/16/2022
* Tag all resources by {AWS-GCR-HLCS-Solutions:Alphafold2} to track overall costs.

### 02/13/2022
* Update to cdk@1.144.0, will update to cdk@v2 later.

### 02/12/2022
* Update policy json.

### 02/01/2022
* Fix install script.

### 02/07/2022
* Update to support run_relax feature.

### 01/20/2022
* Update params.

### 01/19/2022
* Fix some outdated api.

### 01/17/2022
* Support Alpfadold v2.1.1 to predict multimer and params files.
* Change DynamoDB's default setting from provisioned to on-demand.

### 01/15/2022
* Change to use all az in the region to make full use of GPU resources.
* Therefore, the error that no GPU instance in the current AZ has been fixed. Of course, there is no way to do it if the entire region does not.

### 10/24/2021
* Support p4 instances/que，this need manually operate。
* Perfect the sns notification information, now you can see the task name and cost time directly from the mail.
* S3 presigned URL expire in 1day now.

## TODO

* Better authentication mechanism.
* Auto check p4.
* Use Code pipeline to update images.
* The S3N when job successed changed to Eventbridge.
* Use  secondary index in Dynamodb to reverse the id by the job id.
* Frontend pages.

## Known Issue
* If the dataset download is completed really soon when manually selecting the vpc, it may be because the Fsx for lustre is not mounted correctly due to the VPC DNS/DHCP settings. You could ssh into tmp ec2 to manually execute the mount command to test the reason,or just create a new VPC to avoid such questions.check：
https://docs.amazonaws.cn/fsx/latest/LustreGuide/troubleshooting.html 
* jax seems to have a problem with multi GPU scheduling, recommends a maximum of 2GPU.
* CDK Bug。IAM role/DynamoDB/LaunchTemplate/EventBridge's tag cannot be created and need to be added manually.