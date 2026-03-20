-- Add 'body-composition' to the papers.category CHECK constraint.
-- PostgreSQL requires DROP + re-ADD to modify a CHECK constraint.

ALTER TABLE papers DROP CONSTRAINT IF EXISTS papers_category_check;

ALTER TABLE papers ADD CONSTRAINT papers_category_check CHECK (category IN (
    'hypertrophy', 'strength', 'nutrition', 'endurance',
    'recovery', 'mobility', 'programming', 'body-composition', 'general'
));
