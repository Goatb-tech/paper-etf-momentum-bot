FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY README.md ./
RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["paper-etf-bot"]
CMD ["run"]

