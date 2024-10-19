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

