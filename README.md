
# Welcome to your CDK Python project!

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

This stack uses assets, so the toolkit stack must be deployed to the environment

```
$ cdk bootstrap aws://**account**/**region**
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## Changelog

### 10/24/2021
支持p4实例/队列，开启需解除batch.py相关注释。
完善sns通知信息，现在可以从邮件直接看到任务名称和所需时间。


## Changelog

* 引入更完善身份验证机制，但国内没有user pool。
* 自动化鉴别该区域没有p4实例。

问题：
1.如果手动选择vpc后，很快提示数据下载完成，可能是因为VPC DNS/DHCP设置问题导致fsx没有正确挂在，此时可登陆tmp ec2手动执行挂载命令测试原因，参考：
https://docs.amazonaws.cn/fsx/latest/LustreGuide/troubleshooting.html 使用 DNS 名称挂载文件系统失败

解决相关问题后执行cdk destroy --all清除环境，再重新部署。
或者不选择vpc，重新创建即可。

