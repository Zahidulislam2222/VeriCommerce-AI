ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY infra/cloud/runtime-requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /app/requirements.lock
COPY --chown=app:app infra/__init__.py /app/infra/__init__.py
COPY --chown=app:app infra/cloud/__init__.py infra/cloud/settings.py infra/cloud/validator.py infra/cloud/benchmark.py infra/cloud/config.json infra/cloud/snapshot.json infra/cloud/snapshot.sha256 /app/infra/cloud/
USER 10001:10001
