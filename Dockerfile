FROM python:3.12

ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN pip install --no-cache-dir --no-deps -r requirements.txt --prefer-binary

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
