# Archived PostgreSQL Migrations

This directory contains historical Alembic migration scripts from the initial PostgreSQL/Supabase implementation (0001 through 0005).

## Rationale for Archival
Under Phase 6 (MySQL 8.4 qualification and Supabase elimination), the database backend was migrated from PostgreSQL to MySQL 8.4 LTS.
Because PostgreSQL migrations use PostgreSQL-specific DDL syntax (such as partial indexes with `WHERE` clauses, PostgreSQL enum types, and differing dialect datetime precision) and would introduce conflicting revision heads in Alembic, they have been archived in this directory for historical reference and auditability rather than deleted.

The active schema migration chain for MySQL 8.4 begins with `alembic/versions/0001_initial_mysql.py`.
