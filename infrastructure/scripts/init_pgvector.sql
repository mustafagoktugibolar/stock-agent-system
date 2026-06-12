-- Runs once on first container creation (docker-entrypoint-initdb.d).
-- Enables the pgvector extension so Vector columns can be created.
CREATE EXTENSION IF NOT EXISTS vector;
