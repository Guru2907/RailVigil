# ADR-0001: PostgreSQL + PostGIS as the database

Status: accepted (2026-10-17)

## Context
The GIS map, site clustering ("findings within R metres are one site") and map filtering by area need spatial queries. SQLite has none; MySQL's spatial support is weaker; MongoDB would add a second database to run.

## Decision
Use one relational database, PostgreSQL with PostGIS, through SQLAlchemy, GeoAlchemy2 and Alembic. SQLite stays only until Phase 0 moves the backend to Postgres.

## Consequences
Docker Compose is needed for local development. Migrations already exist (Alembic), so the switch is a configuration change plus PostGIS column types.
