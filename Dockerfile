# Use an official Python 3.11 runtime as a parent image. Use the slim version to reduce the image size.
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container to /app
WORKDIR /app

# Copy the entire vertisim directory
COPY ./vertisim /app/vertisim
COPY ./config.json /app/config.json

# Add /app to the PYTHONPATH
ENV PYTHONPATH /app

# Update pip and install packages individually
RUN pip install --no-cache-dir numpy && \
    pip install --no-cache-dir matplotlib && \
    pip install --no-cache-dir networkx && \
    pip install --no-cache-dir geog && \
    pip install --no-cache-dir pandas

RUN pip install --no-cache-dir -r /app/vertisim/requirements.txt

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application
CMD ["uvicorn", "vertisim.api.main:app", "--host", "0.0.0.0", "--port", "5001", "--log-level", "warning"]
