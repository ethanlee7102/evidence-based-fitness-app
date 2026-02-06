-- Add phase_boundaries column to analyses table
-- Stores the Y-coordinates for phase boundary lines (deadlift analysis)

ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS phase_boundaries jsonb;

-- Add comment for documentation
COMMENT ON COLUMN analyses.phase_boundaries IS 'Array of phase boundary objects with y coordinate and between_phases array';
