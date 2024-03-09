FROM python:3.9

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY iss_tracker.py /app/iss_tracker.py
COPY test_iss_tracker.py /test/iss_tracker.py

ENTRYPOINT ["python"]
CMD ["iss_tracker.py"]
