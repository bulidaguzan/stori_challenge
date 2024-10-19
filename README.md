# stori_challenge

## Project Description
It is a system that allows to create users, and process debit and credit transactions and then, send a summary of the statement of account by email.


## Architecture

### AWS
The application was deployed in AWS, using ECR (Elastic Container Registry). 
To update the code of a lambda simply run the upload.sh file located in the same folder.
In this way we can:
- create an image for each lambda
- Upload it to the ECR repository.
- Update the lambda from ECR keeping all the control of the code from the repository.


## System Design
The system was designed to be modular and scalable. 

### Backend that rests on the user
Stack: Python
Framework: FastApi

- auth: Create and authenticate users.
- get_summary: Get the account summary request, and generate the order.
- upload_file: Receive, and upload a txt file to a s3 bucket.


### Core Backend
Stack: Go

- create_summary: Gets the user transactions, formats them and sends them by email.
- process_file: Gets the file inside the BucketS3, and processes it saving the transactions in DynamoDb


