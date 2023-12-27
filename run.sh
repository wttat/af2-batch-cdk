#!/bin/bash

CONFIG_FILE="aws_config.json"


validate_email() {
    if [[ $1 =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$ ]]; then
        echo "true"
    else
        echo "false"
    fi
}

select_aws_region() {
    echo "获取AWS可用的区域列表..."
    local regions_output=$(aws ec2 describe-regions --query 'Regions[*].RegionName' --output text)
    local regions=($regions_output)

    echo "获取到的区域列表: ${regions[*]}"

    if [ ${#regions[@]} -eq 0 ]; then
        echo "未能获取到区域列表。"
        return 1
    fi

    echo "请选择一个区域："
    local i=1
    for region in "${regions[@]}"; do
        echo "$i) $region"
        let i++
    done

    local selection
    read -p "请输入区域的编号: " selection
    if [ $selection -le ${#regions[@]} ] && [ $selection -gt 0 ]; then
        echo "${regions[$selection-1]}"
    else
        echo "无效选择。"
        return 1
    fi
}

select_ec2_keypair() {
    echo "获取当前Region下的EC2密钥对列表..."
    local keypairs_output=$(aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName' --output text)
    local keypairs=($keypairs_output)

    echo "获取到的密钥对列表: ${keypairs[*]}"

    if [ ${#keypairs[@]} -eq 0 ]; then
        echo "在当前Region没有找到EC2密钥对。"
        return 1
    fi

    echo "请选择一个密钥对："
    local i=1
    for keypair in "${keypairs[@]}"; do
        echo "$i) $keypair"
        let i++
    done

    local selection
    read -p "请输入密钥对的编号: " selection
    if [ $selection -le ${#keypairs[@]} ] && [ $selection -gt 0 ]; then
        echo "${keypairs[$selection-1]}"
    else
        echo "无效选择。"
        return 1
    fi
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        read -p "检测到配置文件 $CONFIG_FILE，是否要使用此文件中的参数？(y/n): " use_config
        if [ "$use_config" == "y" ]; then
            echo "加载配置文件..."
            REGION=$(jq -r '.REGION' "$CONFIG_FILE")
            MAIL=$(jq -r '.MAIL' "$CONFIG_FILE")
            KEYPAIR=$(jq -r '.KEYPAIR' "$CONFIG_FILE")
            AUTH=$(jq -r '.AUTH' "$CONFIG_FILE")
            ACCOUNTID=$(jq -r '.ACCOUNTID' "$CONFIG_FILE")
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
    # 选择 AWS 区域
    while true; do
        REGION=$(select_aws_region)
        if [ $? -eq 0 ]; then
            export REGION
            aws configure set default.region $REGION
            break
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
    while true; do
        KEYPAIR=$(select_ec2_keypair)
        if [ $? -eq 0 ]; then
            export KEYPAIR
            break
        fi
    done

    # 读取认证码
    read -p "请输入一个校验码: " AUTH
    export AUTH

    # 获取 AWS 账号 ID 并存储
    ACCOUNTID=$(aws sts get-caller-identity --query Account --output text)
    export ACCOUNTID

    # 保存配置
    save_config
fi

# 执行 CDK 命令
cdk bootstrap aws://${ACCOUNTID}/${REGION}
cdk synth
cdk deploy --all
