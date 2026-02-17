FROM public.ecr.aws/lambda/python:3.11

# Install mariadb-client (for mysqldump) and gzip
# Updates packages and installs mysqldump
RUN dnf update -y && \
    dnf install -y mariadb105 && \
    dnf clean all

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy function code
COPY lambda_function.py .

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.lambda_handler" ]
