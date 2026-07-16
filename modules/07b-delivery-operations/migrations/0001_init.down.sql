-- Migration 0001 — initial schema (DOWN / rollback).
--
-- Drops every object created by 0001_init.up.sql, in reverse dependency order.
-- The runner deletes the 0001 row from schema_migrations after this succeeds.
-- Indexes are dropped implicitly with their tables.

DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS idempotency_keys;
DROP TABLE IF EXISTS ingest_jobs;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tenants;
