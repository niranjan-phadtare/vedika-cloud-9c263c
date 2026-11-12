FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt
COPY astro ./astro
COPY static ./static
COPY assets ./assets
COPY data ./data
RUN python -c "import gzip;from pathlib import Path;p=Path('data/places.sqlite3.gz');p.exists() and Path('data/places.sqlite3').write_bytes(gzip.decompress(p.read_bytes()));p.unlink(missing_ok=True);assert Path('data/places.sqlite3').is_file()"
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY third_party ./third_party
ENV VEDIKA_CLOUD=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 10000
CMD ["sh", "-c", "exec python -m uvicorn astro.api:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log --workers 1"]
