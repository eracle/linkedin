FROM python:3.6

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install -r /requirements/production.txt

WORKDIR /app
