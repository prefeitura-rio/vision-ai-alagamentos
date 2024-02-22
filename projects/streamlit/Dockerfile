ARG PYTHON_VERSION=3.10-slim
FROM python:${PYTHON_VERSION}

# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
# Prevents Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1

# ensures that the python output is sent straight to terminal (e.g. your container log)
# without being first buffered and that you can see the output of your application (e.g. django logs)
# in real time. Equivalent to python -u: https://docs.python.org/3/using/cmdline.html#cmdoption-u
ENV PYTHONUNBUFFERED 1

# Install virtualenv and create a virtual environment
RUN apt-get update && \
    apt-get install --no-install-recommends -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -U poetry && \
    poetry config virtualenvs.create false

# Copy the poetry.lock and pyproject.toml files
# and install dependencies
WORKDIR /tmp
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy the project files into the working directory
WORKDIR /app
COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health


CMD ["streamlit", "run", "projects/streamlit/app/Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
