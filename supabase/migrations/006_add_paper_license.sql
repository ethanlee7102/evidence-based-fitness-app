-- Add license field to papers table for tracking usage rights.
-- Allows filtering corpus to only commercially-usable papers (CC-BY, CC0).

ALTER TABLE papers
ADD COLUMN license TEXT CHECK (license IN (
    'CC0',
    'CC-BY',
    'CC-BY-SA',
    'CC-BY-ND',
    'CC-BY-NC',
    'CC-BY-NC-SA',
    'CC-BY-NC-ND',
    'other',
    'unknown'
)) DEFAULT 'unknown';
