FROM python:3.8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY poetry.lock /code/
COPY pyproject.toml /code/
RUN pip install poetry
RUN poetry install
COPY . /code/
RUN poetry run python manage.py collectstatic --noinput
