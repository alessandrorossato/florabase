import os

os.environ.setdefault("FLORABASE_ENVIRONMENT", "test")
os.environ.setdefault("FLORABASE_DATABASE_URL", "postgresql+psycopg://test:test@db/test")
