FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir .

CMD ["python", "-m", "vertisim.runner", "--env_config", "examples/sfo_sjc/config.json"]
