-- Onboarding Profile Fields
-- Extends profiles table with user onboarding data

ALTER TABLE profiles
ADD COLUMN display_name TEXT,
ADD COLUMN birthday DATE,
ADD COLUMN gender TEXT CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
ADD COLUMN height_cm NUMERIC(5,1),
ADD COLUMN weight_kg NUMERIC(5,1),
ADD COLUMN units_preference TEXT DEFAULT 'metric' CHECK (units_preference IN ('metric', 'imperial')),
ADD COLUMN experience_level TEXT CHECK (experience_level IN ('beginner', 'intermediate', 'advanced')),
ADD COLUMN goal TEXT CHECK (goal IN ('strength', 'build_muscle', 'lose_weight', 'general_fitness', 'cardio_endurance')),
ADD COLUMN workout_days_per_week INTEGER CHECK (workout_days_per_week >= 1 AND workout_days_per_week <= 7),
ADD COLUMN preferred_days TEXT[],
ADD COLUMN injuries_limitations TEXT,
ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN onboarding_completed_at TIMESTAMPTZ;
