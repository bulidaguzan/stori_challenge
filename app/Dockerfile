FROM python:3.9-slim

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy all files in ./src
COPY * ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler.
CMD [ "main.handler" ]