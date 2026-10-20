-- Applied by hand to databases created by `create_all` before 2026-10-06.
-- New tables (company_peers) are created automatically on startup.
BEGIN;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS coverage VARCHAR(16) NOT NULL DEFAULT 'evaluated';
ALTER TABLE source_documents ADD COLUMN IF NOT EXISTS doc_type VARCHAR(64);
ALTER TABLE source_documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE source_documents ADD COLUMN IF NOT EXISTS ingestion_status VARCHAR(16) NOT NULL DEFAULT 'registered';
ALTER TABLE source_documents ADD COLUMN IF NOT EXISTS ingestion_error TEXT;
ALTER TABLE document_chunks ALTER COLUMN embedding DROP NOT NULL;
ALTER TABLE module_findings ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'complete';
ALTER TABLE module_findings ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE module_findings ADD CONSTRAINT module_findings_evaluation_id_module_key UNIQUE (evaluation_id, module);
COMMIT;
