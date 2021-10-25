
# Alphafold2-cdk部署手册

架构图：


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
 * 如需要p4,可解除af2_batch_cdk/batch.py的173-194以及230-239行。
 * `cdk bootstrap aws://ACCOUNT/REGION`
 * `cdk synth`
 * `cdk deploy --all`
 * 确认SNS通知邮件
 * 系统会自动开启一台c5.9xlarge下载数据并存放到FSx for Lustre.和一台P3.2xlarge(可以修改计算环境Min VCPU为0关闭)
 * 3个小时左右数据准备完毕会有邮件通知，此时可以删除临时下载机器准备模型训练
 * 修改目录下的command.json文件
 * 任务提交 curl -X "POST" -H "Authorization: af2" -H "Content-Type: application/json" APIGW——URL -d @command.json
 * 查看任务状态 curl -H "Authorization: af2" APIGW——URL/{id}
 * 任务分析完毕会有邮件通知，用户可以到指定的S3桶下载pdb文件进行在云端或者本地查看。

Enjoy!

## Changelog

### 10/24/2021
* 支持p4实例/队列，开启需解除batch.py相关注释。
* 完善sns通知信息，现在可以从邮件直接看到任务名称和所需时间。
* S3 presigned URL expire in 1day

## TODO

* 引入更完善身份验证机制，但国内没有user pool。
* 自动化鉴别该区域没有p4实例。

## Known Issue
* 有可能默认AZ没有p3实例，导致初始化失败。
* 如果手动选择vpc后，很快提示数据下载完成，可能是因为VPC DNS/DHCP设置问题导致fsx没有正确挂载，此时可登陆tmp ec2手动执行挂载命令测试原因，参考：
https://docs.amazonaws.cn/fsx/latest/LustreGuide/troubleshooting.html 使用 DNS 名称挂载文件系统失败。