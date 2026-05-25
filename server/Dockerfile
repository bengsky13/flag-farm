# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /server

# Copy the requirements file first to leverage Docker caching
# (Make sure to create a requirements.txt with flask, etc.)
COPY . .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5002
RUN ls
CMD ["./start_server.sh"]