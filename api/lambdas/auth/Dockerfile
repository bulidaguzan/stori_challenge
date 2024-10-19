FROM public.ecr.aws/lambda/python:3.11
# Copy function code
COPY . ${LAMBDA_TASK_ROOT}
# Install the function's dependencies using file requirements.txt
COPY requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}" -U --no-cache-dir

CMD [ "main.handler" ]