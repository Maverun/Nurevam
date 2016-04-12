FROM python:3
COPY . /
RUN apt-get install libffi-dev
RUN pip install --upgrade -r requirements.txt
CMD ["python", "bot.py"]
