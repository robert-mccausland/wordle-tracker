FROM python:3.11-alpine

RUN apk add --no-cache make

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY Makefile manage.py ./docker/entrypoint.sh ./
COPY ./apps ./apps
COPY ./services ./services
COPY ./wordletracker ./wordletracker

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["make", "run-bot"]
