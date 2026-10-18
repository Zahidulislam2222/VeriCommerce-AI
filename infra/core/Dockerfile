ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /var/cache/vericommerce && chown app:app /var/cache/vericommerce
COPY requirements.txt requirements.lock build-requirements.lock os-requirements.lock build_os.py ./
RUN python build_os.py --lock os-requirements.lock --execute
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: --no-deps -r build-requirements.lock \
    && python -m pip install --no-cache-dir --require-hashes --only-binary=:all: --no-deps -r requirements.lock \
    && python -m pip check \
    && python -m pip uninstall --yes pip \
    && python -c "import pathlib, shutil, sysconfig; folder = pathlib.Path(sysconfig.get_path('stdlib')) / 'ensurepip'; shutil.rmtree(folder) if folder.exists() else None"
COPY --chown=app:app . /app
USER 10001:10001
