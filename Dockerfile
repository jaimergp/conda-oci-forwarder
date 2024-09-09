# Use the official Python image as the base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the working directory
COPY . /app

# Install the application dependencies
RUN pip install -r requirements.txt

EXPOSE 8000

# Define the entry point for the container
CMD ["fastapi", "run", "--host=0.0.0.0", "--port=8000", "app.py"]
