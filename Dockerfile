FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/streamlit/streamlit-example.git .

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# copy the application
COPY app .

EXPOSE 8000

# Command to run the application
ENTRYPOINT ["streamlit", "run", "app/app.py", "--server.port=8000", "--server.address=0.0.0.0"]