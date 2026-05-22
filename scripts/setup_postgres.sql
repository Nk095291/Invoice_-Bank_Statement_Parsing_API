-- Run as PostgreSQL superuser (e.g. psql -U postgres -f scripts/setup_postgres.sql)
CREATE USER documents_user WITH PASSWORD 'documents_pass';
CREATE DATABASE documents_db OWNER documents_user;
GRANT ALL PRIVILEGES ON DATABASE documents_db TO documents_user;
