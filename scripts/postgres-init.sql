CREATE ROLE app_runtime LOGIN PASSWORD 'local_runtime_only';
GRANT CONNECT ON DATABASE timekeeping TO app_runtime;
GRANT USAGE, CREATE ON SCHEMA public TO app_runtime;
