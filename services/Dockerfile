FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY api/ .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
