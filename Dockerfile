
FROM python:3.11

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY ./vertisim /vertisim

WORKDIR /vertisim

CMD ["python3", "inputs.py"]


