FROM python:3.13-slim

WORKDIR /app/services/api

RUN pip install --no-cache-dir uv

COPY api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY api/ .
# services/telemetry es sibling de services/api (routes/telemetry.py lo
# importa vía sys.path relativo, ver Project 6.3) — se copia manteniendo
# la misma profundidad relativa que en el checkout local.
COPY telemetry/ /app/services/telemetry

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
