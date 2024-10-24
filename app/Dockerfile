FROM python:3.9-slim

ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install awslambdaric

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt

# Asegurarse que el directorio routes se copia correctamente
COPY ./routes/ ${LAMBDA_TASK_ROOT}/routes/
# Copiar los archivos restantes
COPY *.py ${LAMBDA_TASK_ROOT}/

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "main.handler" ]