# Use an official Python 3.12 runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Configure pip to use China mirrors and install dependencies
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --upgrade pip && \
    pip install --root-user-action=ignore -r requirements.txt

# Make port 3000 available to the world outside this container
EXPOSE 8000

# Run main.py when the container launches
CMD ["bash", "-c", "python3 app.py"]

