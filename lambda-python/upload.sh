aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 314146307016.dkr.ecr.us-east-1.amazonaws.com

docker build -t stori_challenge .

docker tag stori_challenge:latest 314146307016.dkr.ecr.us-east-1.amazonaws.com/stori_challenge:python_latest

docker push 314146307016.dkr.ecr.us-east-1.amazonaws.com/stori_challenge:python_latest