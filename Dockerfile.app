FROM python:3.10 as builder

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt


FROM python:3.10-alpine
ENV PYTHONUNBUFFERED 1
COPY --from=builder /install /usr/local
COPY . /app
RUN apk --no-cache add libpq
WORKDIR /app
ENTRYPOINT python3.10 run_bot.py
