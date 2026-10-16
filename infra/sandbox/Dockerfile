# Vortex code sandbox: runs user/model Python with data libraries, no network, no privileges.
#
#   docker build -t vortex-sandbox infra/sandbox
#
# The API runs it with: --network none --read-only --cap-drop ALL --memory/--cpus/--pids-limit,
# a time limit, user nobody, the chat's files mounted read-only at /data and /out for charts.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp \
    HOME=/tmp

RUN pip install numpy pandas matplotlib openpyxl scipy tabulate \
    && python -c "import matplotlib.pyplot"

COPY runner.py /opt/vortex/runner.py

USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python", "-I", "/opt/vortex/runner.py"]
