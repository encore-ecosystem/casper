FROM python:3.12-bookworm
LABEL authors="kotto"

COPY . .

EXPOSE 8569
RUN ["python3", "-m", "pip", "install", "-r", "requirements.txt"]
ENTRYPOINT ["python3", "main.py", "-s", "8569"]