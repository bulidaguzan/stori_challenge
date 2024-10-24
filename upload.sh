#!/bin/bash

# Required parameters
LAMBDA_NAME=$1
IMAGE_TAG=$2
DOCKERFILE_PATH=$3

if [ -z "$LAMBDA_NAME" ] || [ -z "$IMAGE_TAG" ] || [ -z "$DOCKERFILE_PATH" ]; then
    echo "Usage: $0 <lambda-name> <image-tag> <dockerfile-path>"
    echo "Example: $0 auth-lambda latest src/auth"
    exit 1
fi

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT="314146307016"
ECR_REPO="stori_challenge"

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project root: ${PROJECT_ROOT}"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Clean up old images locally
echo "🧹 Cleaning up old local images..."
docker images --format '{{.Repository}}:{{.Tag}}' | grep "^${ECR_REPO}" | xargs -r docker rmi -f

# Build the Docker image
echo "Dockerfile path: ${PROJECT_ROOT}/${DOCKERFILE_PATH}/Dockerfile"
echo "🏗️ Building Docker image..."
docker build \
    --build-arg LAMBDA_NAME=${LAMBDA_NAME} \
    --no-cache \
    -t ${ECR_REPO}:${IMAGE_TAG} \
    -f ${PROJECT_ROOT}/${DOCKERFILE_PATH}/Dockerfile \
    "${PROJECT_ROOT}/${DOCKERFILE_PATH}"

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

# Tag the image
echo "🏷️ Tagging image..."
docker tag ${ECR_REPO}:${IMAGE_TAG} \
    ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}

# Push the image to ECR
echo "⬆️ Pushing image to ECR..."
docker push ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Failed to push image to ECR"
    exit 1
fi

# Force update Lambda function
echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
    --function-name ${LAMBDA_NAME} \
    --image-uri ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG} \
    --region ${AWS_REGION} \
    --publish

if [ $? -ne 0 ]; then
    echo "❌ Failed to update Lambda function"
    exit 1
fi

# Verify the update
echo "🔍 Verifying Lambda update..."
CURRENT_IMAGE=$(aws lambda get-function \
    --function-name ${LAMBDA_NAME} \
    --region ${AWS_REGION} \
    --query 'Code.ImageUri' \
    --output text)

echo "Current Lambda image: ${CURRENT_IMAGE}"
echo "✅ Deployment completed successfully!"