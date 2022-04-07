
# Alphafold2-cdk部署手册

参考blog：https://aws.amazon.com/cn/blogs/china/one-click-construction-of-a-highly-available-protein-structure-prediction-platform-on-the-cloud-part-one/

架构图参考：
![avatar](architecture.png)

## 优化Alphafold2镜像源代码库：

https://github.com/wttat/alphafold

## 部署所需IAM权限请参考policy.json

## 部署流程，基于Amazon Linux 2 

 * 安装node和npm。
 * `wget https://nodejs.org/dist/v14.18.1/node-v14.18.1-linux-x64.tar.xz`  
 * `tar xvf node-v14.18.1-linux-x64.tar.xz`
 * `sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/node /usr/local/bin` 
 * `sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/npm /usr/local/bin`
 * 配置PATH环境变量。
 * `export PATH=$PATH:$(npm get prefix)/bin`
 * 安装git。
 * `sudo yum install -y git`
 * 克隆本repo。
 * `git clone https://github.com/wttat/af2-batch-cdk`
 * `cd af2-batch-cdk`
 * 安装所需依赖。
 * `pip3 install -r requirements.txt`
 * 注：如果国内下载pip包过慢，可以使用清华pip源。
 * `pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
 * 安装cdk。
 * `npm install -g aws-cdk@1.144.0`
 * 修改app.py内28～37，如需要nicedcv，可解除75-84行注释。
 * 如需要p4,可解除af2_batch_cdk/batch.py的173-194以及230-239行注释。
 * 如本region从未运行过cdk，需要以下脚本初始化。
 * `cdk bootstrap aws://{ACCOUNT}/{REGION}`
 * 通过cdk生成cloudformation模板
 * `cdk synth`
 * 部署所有堆栈。
 * `cdk deploy --all`
 * 确认SNS通知邮件
 * 系统会自动开启一台c5.9xlarge下载数据并存放到FSx for Lustre。
 * 3个小时左右数据准备完毕会有邮件通知，此时可以删除临时下载机器，开始任务。
 * 修改目录下的command.json文件
 * 任务提交 curl -X "POST" -H "Authorization: af2" -H "Content-Type: application/json" APIGW——URL -d @command.json
 * 查看任务状态 curl -H "Authorization: af2" APIGW——URL/{id}
 * 任务分析完毕会有邮件通知，用户可以到指定的S3桶下载pdb文件进行在云端或者本地查看。

<<<<<<< Updated upstream
=======
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
5. Install CDK@v1
```
npm install -g aws-cdk@1.150.0
```
6. Install dependancy
```
pip3 install -r requirements.txt
```
& if in China 
```
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
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

      - Use a existed vpc:
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
      
      Note: You have to do this at the same time.

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
4. num_multimer_predictions_per_model.type:string(bool).type:int.Default:[5]:

    Controls how many predictions will be made per model, by default the offline system will run each model 5 times for a total of 25 predictions.

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

7. DELETE ONE:DELETE finished or failed job,change the KEY(if set) and ApiGW_URL to your own,the id of job could be searched via GET ALL or POST: 

```
curl -X "DELETE" -H "Authorization: {KEY}"  {ApiGW_URL}/{id}
```
>>>>>>> Stashed changes
Enjoy!

## command.json 参数说明

* fasta 必填：蛋白质名称，可自定义。
* file_name 必填:氨基酸序列文件名称，必须与S3存储桶中的input文件名对应。
* db_preset [reduced_dbs/full_dbs] 必选: （1）reduced_dbs: This preset is optimized for speed and lower hardware requirements. It runs with a reduced version of the BFD database. It requires 8 CPU cores (vCPUs), 8 GB of RAM, and 600 GB of disk space.（2）full_dbs: This runs with all genetic databases used at CASP14.
* model_preset [monomer/monomer_casp14/monomer_ptm/multimer] 必选：（1）monomer（单体）: This is the original model used at CASP14 with no ensembling。（2）monomer_casp14*: This is the original model used at CASP14 with num_ensemble=8, matching our CASP14 configuration. This is largely provided for reproducibility as it is 8x more computationally expensive for limited accuracy gain (+0.1 average GDT gain on CASP14 domains).（3）monomer_ptm: This is the original CASP14 model fine tuned with the pTM head, providing a pairwise confidence measure. It is slightly less accurate than the normal monomer model.（4）multimer（多聚体）: This is the AlphaFold-Multimer (https://github.com/deepmind/alphafold#citing-this-work) model. To use this model, provide a multi-sequence FASTA file. In addition, the UniProt database should have been downloaded.
* run_relax.[true/false],Default:[true],Whether to run the final relaxation step on the predicted models. Turning relax off might result in predictions with distracting stereochemical violations but might help in case you are having issues with the relaxation stage.
* is_prokaryote_list.[true/false],Default:[false],true for homomer,false for heteromer.only works when multimer
* max_template_date.Default:[2021-11-01]: 数据库扫描截止日期。详见alphafold官方库解释，建议设置为当天。
* que [low/mid/high/p4]：分别对应p3.2xlarge、p3.8xlarge、p3.16xlarge和p4d.24xlarge,其中p4因为区域支持不多，需要手动启用代码中注释。目前每个任务默认分配一块卡。
* comment：本次任务注释，自行填写。
* gpu.Default:[1],number of GPU。p3实例下，每个gpu对应8vcpu，60G内存；p4实例下，每个gpu对应12vcpu，140G内存。
  
注：GPU数量太多意义不大，目前来看超过1000aa的一块V100的显存不够，但是太多也是浪费，因为AF2推理的时候还是只用一块卡。

## 目前数据集版本：

<<<<<<< Updated upstream
* dataset3.tar.gz 模型更新为alphafold_params_2022-01-19.tar。
* dataset2.tar.gz 更新了multimer需要的数据集和参数。
* dataset.tar.gz 原始版本。

## Changelog

=======
## Total cost calculate：
* The cost filed in DynamoDB counts the number of seconds each task runs. 
* Use tag {AWS-GCR-HLCS-Solutions:Alphafold2} to track total cost. Check:https://docs.aws.amazon.com/zh_cn/awsaccountbilling/latest/aboutv2/activating-tags.html

## Current dataset version：

1. dataset4.tar.gz

   update params to alphafold_params_2022-03-02.tar. Update multimer models to v2.
2. dataset3.tar.gz
    
    update params to alphafold_params_2022-01-19.tar.
3. dataset2.tar.gz
    
    update the dataset and params used by multimer.
4. dataset.tar.gz

    original version.

## Changelog

### 04/07 2022
* Support Alphafold v2.2.0, the is_prokaryote_list parameter has been removed, add a new one :num_multimer_predictions_per_model. 

### 03/31/2022
* Update aws-cdk to @1.150.0

>>>>>>> Stashed changes
### 02/16/2022
* 将所有资源加入标签{AWS-GCR-HLCS-Solutions:Alphafold2},方便追踪总体成本。

### 02/13/2022
* 更新支持cdk@1.144.0，后续切到cdk v2。
* 由此又修复了一个因为cdk导致Api GW不能invoke lambda的奇怪bug..

### 02/12/2022
* 增加权限json。

### 02/01/2022
* 修复安装脚本。

### 02/07/2022
* 更新支持run_relax参数。

### 01/20/2022
* 数据集模型更新为alphafold_params_2022-01-19.tar。

### 01/19/2022
* 修复了过期api

### 01/17/2022
* 支持Alpfadold v2.1.1 关于multimer的预测，参数也对应更新。
* DynamoDB默认从预置更改为按需计费。

### 01/15/2022
* 更改为使用当前region所有AZ，充分利用GPU资源。
* 因此修复了当前AZ没有GPU实例的报错，当然全region都没有就没办法了。

### 10/24/2021
* 支持p4实例/队列，开启需解除batch.py相关注释。
* 完善sns通知信息，现在可以从邮件直接看到任务名称和所需时间。
* S3 presigned URL expire in 1day

## TODO

* 引入更完善身份验证机制，但国内没有user pool。
* 自动化鉴别该区域没有p4实例。
* Code pipeline更新。
* 成功时的S3N，改成Eventbridge。
* Dynamodb加入二级索引，用来通过job id反推id。
* 前端页面。

## Known Issue
* 如果手动选择vpc后，很快提示数据下载完成，可能是因为VPC DNS/DHCP设置问题导致fsx没有正确挂载，此时可登陆tmp ec2手动执行挂载命令测试原因，建议统一使用新建VPV。参考：
https://docs.amazonaws.cn/fsx/latest/LustreGuide/troubleshooting.html 使用 DNS 名称挂载文件系统失败。
* jax似乎对4GPU调度有问题，建议使用2GPU。
* CDK Bug。IAM role/DynamoDB/LaunchTemplate/EventBridge不能创造标签，需要手动补充。