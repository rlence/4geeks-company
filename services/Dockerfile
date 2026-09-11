FROM python:3.13-slim

WORKDIR /app/services/api

RUN pip install --no-cache-dir uv

COPY services/api/requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY services/api/ .
# services/telemetry, services/reporting y data/pipelines|process son
# módulos planos sibling de services/api, alcanzados por sys.path
# relativo (ver context/plans/hito6-part-2.md) — se copian manteniendo
# la misma profundidad relativa que en el checkout local. Por eso el
# build context de este Dockerfile es la raíz del repo, no ./services.
COPY services/telemetry/ /app/services/telemetry
COPY services/reporting/ /app/services/reporting
COPY data/pipelines/ /app/data/pipelines
COPY data/process/ /app/data/process

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
