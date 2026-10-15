-- Migration 002: Complaint Resolution Tracking
-- Adds resolved_at timestamp and resolution_notes to the complaints table
-- Compatible with MySQL 8 and existing schema

ALTER TABLE complaints
    ADD COLUMN resolved_at DATETIME DEFAULT NULL,
    ADD COLUMN resolution_notes TEXT DEFAULT NULL;
