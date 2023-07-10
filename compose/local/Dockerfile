FROM python:3.8

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install -r /requirements/local.txt

COPY ./compose/production/wait-for-selenium /wait-for-selenium
RUN sed -i 's/\r$//g' /wait-for-selenium
RUN chmod +x /wait-for-selenium

WORKDIR /app
