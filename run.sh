#!/bin/bash

# Function to validate email
validate_email() {
    if [[ $1 =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$ ]]; then
        echo "true"
    else
        echo "false"
    fi
}

# Function to list AWS regions and let the user select one
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
        echo "已选择区域: ${regions[$selection-1]}"
        echo "${regions[$selection-1]}"
    else
        echo "无效选择。"
        return 1
    fi
}



# Function to list EC2 key pairs and let the user select one
select_ec2_keypair() {
    echo "获取当前Region下的EC2密钥对列表..."
    local keypairs=($(aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName' --output text))

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

# Select AWS region
while true; do
    REGION=$(select_aws_region)
    if [ $? -eq 0 ]; then
        export REGION
        aws configure set default.region $REGION
        break
    fi
done

# Read and validate email
while true; do
    read -p "请输入您的邮箱: " MAIL
    if [ $(validate_email "$MAIL") == "true" ]; then
        export MAIL
        break
    else
        echo "邮箱格式不正确，请重新输入."
    fi
done

# Select and check EC2 key pair
while true; do
    KEYPAIR=$(select_ec2_keypair)
    if [ $? -eq 0 ]; then
        export KEYPAIR
        break
    fi
done

# Read authentication code
read -p "请输入一个校验码: " AUTH
export AUTH

# Get AWS Account ID and store it
ACCOUNTID=$(aws sts get-caller-identity --query Account --output text)
export ACCOUNTID

# Execute CDK commands
cdk bootstrap aws://${ACCOUNTID}/${REGION}
cdk synth
cdk deploy --all
