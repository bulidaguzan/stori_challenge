#!/bin/bash

# Required parameters
LAMBDA_NAME=$1
IMAGE_TAG=$2
DOCKERFILE_PATH=$3

if [ -z "$LAMBDA_NAME" ] || [ -z "$IMAGE_TAG" ] || [ -z "$DOCKERFILE_PATH" ]; then
    echo "Usage: $0 <lambda-name> <image-tag> <lambda-path>"
    echo "Example: $0 auth lambda_auth"
    exit 1
fi

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT="314146307016"
ECR_REPO="stori_challenge"

# Get project root (one level up from shared)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project root: ${PROJECT_ROOT}"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build the Docker image
echo "Dockerfile root:${PROJECT_ROOT}/${DOCKERFILE_PATH}/Dockerfile"
echo "🏗️ Building Docker image..."

docker build \
    --build-arg LAMBDA_NAME=${LAMBDA_NAME} \
    -t ${ECR_REPO}:${IMAGE_TAG} \
    -f ${PROJECT_ROOT}/${DOCKERFILE_PATH}/Dockerfile \
    /${PROJECT_ROOT}/${DOCKERFILE_PATH}


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

# Update Lambda function
echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
    --no-paginate \
    --function-name ${LAMBDA_NAME} \
    --image-uri ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG} \
    --region ${AWS_REGION}

echo "✅ Deployment completed successfully!"