# Infosalud Nexus — servicio para agentes (ADR-013)
# Sólo stdlib: la imagen es runtime, no dependencia de código.
FROM python:3.13-slim
WORKDIR /srv
COPY infosalud/ ./infosalud/
COPY pyproject.toml ./
EXPOSE 8081
CMD ["python3", "-m", "infosalud", "servir", "--host", "0.0.0.0", "--puerto", "8081"]
