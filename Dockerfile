FROM python:3-slim

workdir /app

COPY . .
RUN pip3 install -r requirements.txt

expose 5000

CMD ["python", "app.py"]