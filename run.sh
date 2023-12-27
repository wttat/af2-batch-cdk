#!/bin/bash
set -e
CONFIG_FILE="af2_config.json"
echo "初始化参数。。" 

validate_email() {
    if [[ $1 =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$ ]]; then
        echo "true"
    else
        echo "false"
    fi
}


load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        cat $CONFIG_FILE
        read -p "检测到配置文件 $CONFIG_FILE，是否要使用此文件中的参数？(y/n): " use_config
        if [ "$use_config" == "y" ]; then
            echo "加载配置文件..."
            export REGION=$(jq -r '.REGION' "$CONFIG_FILE")
            export MAIL=$(jq -r '.MAIL' "$CONFIG_FILE")
            export KEYPAIR=$(jq -r '.KEYPAIR' "$CONFIG_FILE")
            export AUTH=$(jq -r '.AUTH' "$CONFIG_FILE")
            export ACCOUNTID=$(jq -r '.ACCOUNTID' "$CONFIG_FILE")
            return 0
        fi
    fi
    return 1
}

save_config() {
    jq -n \
        --arg REGION "$REGION" \
        --arg MAIL "$MAIL" \
        --arg KEYPAIR "$KEYPAIR" \
        --arg AUTH "$AUTH" \
        --arg ACCOUNTID "$ACCOUNTID" \
        '{REGION: $REGION, MAIL: $MAIL, KEYPAIR: $KEYPAIR, AUTH: $AUTH, ACCOUNTID: $ACCOUNTID}' \
        > "$CONFIG_FILE"
}

if ! load_config; then

    echo "手动选择配置"
    echo "获取AWS可用的区域列表..."
    regions=$(aws ec2 describe-regions --query 'Regions[*].RegionName' --output text)
    echo "请选择一个区域的编号: "
    select choice in $regions; do
        if [ -n "$choice" ]; then
            REGION="$choice"
            export REGION
            aws configure set default.region $REGION
            break
        else
            echo "无效选择。"
        fi
    done

    # 读取并验证电子邮件
    while true; do
        read -p "请输入您的邮箱: " MAIL
        if [ $(validate_email "$MAIL") == "true" ]; then
            export MAIL
            break
        else
            echo "邮箱格式不正确，请重新输入."
        fi
    done

    # 选择并检查 EC2 密钥对
    echo "获取当前Region下的EC2密钥对列表..."
    keypairs=$(aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName' --output text)
    echo "请选择一个密钥对的编号: "
    select choice in $keypairs; do
        if [ -n "$choice" ]; then
            KEYPAIR="$choice"
            export KEYPAIR
            break
        else
            echo "无效选择。"
        fi
    done

    # 读取认证码
    read -p "请输入API的鉴权码 " AUTH
    export AUTH

    echo "参数获取完毕，准备生成配置文件。"

    # 获取 AWS 账号 ID 并存储
    ACCOUNTID=$(aws sts get-caller-identity --query Account --output text)
    export ACCOUNTID

    # 保存配置
    save_config

    echo "配置文件已保存"
fi

echo "准备执行CDK部署"

echo "KEYPAIR:"$KEYPAIR
echo "MAIL:"$MAIL
echo "AUTH:"$AUTH
# 执行 CDK 命令
echo "CDK 初始化开始。。"
cdk bootstrap aws://${ACCOUNTID}/${REGION}
echo "CDK 初始化结束。。"

echo "准备生成CDK模板"
cdk synth
echo "CDK模板生成结束"


# 根据 REGION 的值决定部署哪些堆栈
if [[ "$REGION" == "cn-north-1" || "$REGION" == "cn-northwest-1" ]]; then
    read -p "注意：目前位于AWS中国区域，访问Github可能会超时，导致Sagemaker notebook部署失败，建议单独部署。确认部署Sagemaker notebook 实例？(y/n): " deploy_notebook
    if [ "$deploy_notebook" == "y" ]; then
        echo "部署所有 CDK 堆栈..."
        cdk deploy --all
    else
        echo "部署指定的 CDK 堆栈..."
        cdk deploy BATCHCdkStack APIGWCdkStack VPCCdkStack
    fi
else
    echo "部署所有 CDK 堆栈..."
    cdk deploy --all
fi