-- Add FPS column to videos table for landmark visualization sync
alter table videos add column if not exists fps real;
