FROM python:3.11

WORKDIR /code

RUN pip install --no-cache-dir -U poetry
RUN poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml ./
COPY ./libs /code/libs
RUN poetry lock --no-update && poetry install --no-dev --no-interaction --no-ansi

COPY ./app /code/app
COPY ./migrations /code/migrations
COPY ./compose-entrypoint.sh /code

RUN chmod +x /code/compose-entrypoint.sh

ENTRYPOINT ["/code/compose-entrypoint.sh"]
