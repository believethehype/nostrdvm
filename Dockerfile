# Use the official Python 3.12 image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

RUN pip install setuptools

# Copy the rest of the application code into the container
COPY . .

#RUN pip install nostr-dvm
RUN python setup.py install

# Specify the command to run your application
CMD ["python3", "-u", "main.py"]
