
# Alphafold2-cdk部署手册

参考blog：https://aws.amazon.com/cn/blogs/china/one-click-construction-of-a-highly-available-protein-structure-prediction-platform-on-the-cloud-part-one/

## 优化Alphafold2镜像源代码库：

https://github.com/wttat/alphafold

## 部署流程

 * `wget https://nodejs.org/dist/v14.18.1/node-v14.18.1-linux-x64.tar.xz`  
 * `tar xvf node-v14.18.1-linux-x64.tar.xz`
 * `sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/node /usr/local/bin` 
 * `sudo ln -s /home/ec2-user/node-v14.18.1-linux-x64/bin/npm /usr/local/bin`
 * `export PATH=$PATH:$(npm get prefix)/bin`
 * `sudo yum install -y git`
 * `git clone https://github.com/wttat/af2-batch-cdk`
 * `cd af2-batch-cdk`
 * `pip3 install -r requirements.txt`
 * `npm install -g aws-cdk`
 * 修改app.py内28～37，如需要nicedcv，可解除75-84行注释。
 * 如需要p4,可解除af2_batch_cdk/batch.py的173-194以及230-239行注释。
 * `cdk bootstrap aws://{ACCOUNT}/{REGION}`
 * `cdk synth`
 * `cdk deploy --all`
 * 确认SNS通知邮件
 * 系统会自动开启一台c5.9xlarge下载数据并存放到FSx for Lustre.和一台P3.2xlarge(可以修改计算环境Min VCPU为0关闭)
 * 3个小时左右数据准备完毕会有邮件通知，此时可以删除临时下载机器，开始任务。
 * 修改目录下的command.json文件
 * 任务提交 curl -X "POST" -H "Authorization: af2" -H "Content-Type: application/json" APIGW——URL -d @command.json
 * 查看任务状态 curl -H "Authorization: af2" APIGW——URL/{id}
 * 任务分析完毕会有邮件通知，用户可以到指定的S3桶下载pdb文件进行在云端或者本地查看。

Enjoy!

cdk依赖有问题的话用 --use-feature=2020-resolver

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

* dataset.tar.gz 原始版本。
* dataset2.tar.gz 更新了multimer需要的数据集和参数。
* dataset3.tar.gz 模型更新为alphafold_params_2022-01-19.tar。


## Changelog

### 01/19/2022
* 修复了过期api

### 02/07/2022
* 更新支持run_relax参数

### 01/20/2022
* 数据集模型更新为alphafold_params_2022-01-19.tar"

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
* 如果手动选择vpc后，很快提示数据下载完成，可能是因为VPC DNS/DHCP设置问题导致fsx没有正确挂载，此时可登陆tmp ec2手动执行挂载命令测试原因，参考：
https://docs.amazonaws.cn/fsx/latest/LustreGuide/troubleshooting.html 使用 DNS 名称挂载文件系统失败。

