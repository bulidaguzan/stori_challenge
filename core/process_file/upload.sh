aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 314146307016.dkr.ecr.us-east-1.amazonaws.com

# Build con nombre específico
docker build -t stori_process_file .

# Tag con nombre específico
docker tag lambda_process_file:latest 314146307016.dkr.ecr.us-east-1.amazonaws.com/stori_challenge:lambda_process_file

# Push
docker push 314146307016.dkr.ecr.us-east-1.amazonaws.com/stori_challenge:lambda_process_file