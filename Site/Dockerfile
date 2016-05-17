FROM python:3-onbuild
ADD requirements.txt /requirements.txt
RUN pip install -r requirements.txt
ADD . /
EXPOSE 5000
CMD [ "gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000","app:app" ]
