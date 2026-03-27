-- Add 3 new muscle groups for exercise library overhaul
-- Hip Adductors (new "Adductors" category), Neck (new "Neck" category),
-- Rotator Cuff (under existing "Shoulders" category)

INSERT INTO muscle_groups (name, category, display_order) VALUES
    ('Hip Adductors', 'Adductors', 34),
    ('Neck', 'Neck', 35),
    ('Rotator Cuff', 'Shoulders', 36);
