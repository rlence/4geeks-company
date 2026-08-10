FROM node:22-alpine

# WORKDIR es /app/uis (no /app): backoffice importa packages/data-utils con una ruta
# relativa fija de 4 niveles ("../../../../packages/data-utils", ver
# .agents/rules/monorepo-imports.md). Mantener este nivel de anidamiento hace que ese
# import resuelva a /app/packages/data-utils, que docker-compose.yml monta ahí en runtime.
WORKDIR /app/uis

COPY website/package.json website/package-lock.json ./website/
RUN cd website && npm ci

COPY backoffice/package.json backoffice/package-lock.json ./backoffice/
RUN cd backoffice && npm ci

COPY website ./website
COPY backoffice ./backoffice
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 3000 3001
CMD ["./start.sh"]
