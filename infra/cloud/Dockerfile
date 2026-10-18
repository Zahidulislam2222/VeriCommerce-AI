ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY infra/cloud/runtime-requirements.lock /app/requirements.lock
COPY backend/build-requirements.lock /app/build-requirements.lock
COPY backend/os-requirements.lock backend/build_os.py /app/
RUN python build_os.py --lock os-requirements.lock --execute
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: --no-deps -r build-requirements.lock \
    && python -m pip install --no-cache-dir --require-hashes --only-binary=:all: --no-deps -r requirements.lock \
    && python -m pip check \
    && python -m pip uninstall --yes pip \
    && python -c "import pathlib, shutil, sysconfig; folder = pathlib.Path(sysconfig.get_path('stdlib')) / 'ensurepip'; shutil.rmtree(folder) if folder.exists() else None"
COPY --chown=app:app infra/__init__.py /app/infra/__init__.py
COPY --chown=app:app infra/cloud/__init__.py infra/cloud/settings.py infra/cloud/validator.py infra/cloud/benchmark.py infra/cloud/config.json infra/cloud/snapshot.json infra/cloud/snapshot.sha256 /app/infra/cloud/
USER 10001:10001
