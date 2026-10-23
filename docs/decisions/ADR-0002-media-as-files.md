# ADR-0002: Media files in storage, not in the database

Status: accepted (2026-10-17)

## Context
Every upload produces originals, annotated outputs, evidence crops and thumbnails. Storing them as BLOBs or GridFS documents bloats backups and slows queries.

## Decision
Files go to object storage behind a `StorageService` interface — local disk now, MinIO (S3-compatible) later. The database stores storage keys, sizes, checksums and EXIF metadata only.

## Consequences
Backups have two parts (database dump + storage bucket). Switching storage backends touches only `StorageService`.
