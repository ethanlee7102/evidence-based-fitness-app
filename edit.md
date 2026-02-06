Ready to code?                                                                      
                                                                                                                                                                                                                    
 Here is Claude's plan:                                                                                                                                                                                           
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Deadlift Analysis Overhaul - Planning                                                                                                                                                                              
                                                                                                                                                                                                                    
 Current Capabilities                                                                                                                                                                                               
                                                                                                                                                                                                                    
 Available Landmarks (per frame)                                                                                                                                                                                    
 ┌───────────┬─────────┬────────────────────────────────────────┐
 │ Body Part │ Indices │           Currently Used For           │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Shoulders │ 11, 12  │ Back angle calculation                 │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Elbows    │ 13, 14  │ Not used                               │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Wrists    │ 15, 16  │ Bar path tracking (midpoint)           │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Hips      │ 23, 24  │ Hip angle, back angle                  │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Knees     │ 25, 26  │ Not used (only smoothed for occlusion) │
 ├───────────┼─────────┼────────────────────────────────────────┤
 │ Ankles    │ 27, 28  │ Anchored for occlusion handling        │
 └───────────┴─────────┴────────────────────────────────────────┘
 Angles We Can Calculate

 1. Hip Angle (shoulder-hip-knee): Joint angle, currently used for lockout check only
 2. Knee Angle (hip-knee-ankle): Joint angle, available but NOT currently used
 3. Back Angle from Horizontal: Angle of hip-shoulder line relative to horizontal through hips
 4. Thigh Angle from Horizontal: Angle of hip-knee line relative to horizontal through hips
 5. Shin Angle (vertical angle of knee-to-ankle line): Can be added

 Metrics We Can Calculate

 - Bar path horizontal drift
 - Bar path straightness (detects S-curves)
 - Position changes over time (velocity could be added)
 - Frame-by-frame joint positions

 ---
 Phase-Based Analysis (User Decision)

 Phase Detection Method (Wrist Vertical Range)

 1. Find min wrist Y (start position) and max wrist Y (lockout position)
   - Note: In normalized coords, lower Y = higher on screen
 2. Calculate total vertical travel: range = start_y - end_y
 3. Divide range into equal segments for phases

 Example (3 phases):

 Start: wrist_y = 0.80 (bar on floor)
 End:   wrist_y = 0.35 (lockout)
 Range: 0.45

 Phase 1 (bottom third):  0.80 → 0.65
 Phase 2 (middle third):  0.65 → 0.50
 Phase 3 (top third):     0.50 → 0.35

 Multi-Rep Handling

 - Analyze first rep only
 - Detect rep completion when wrist reaches highest point and starts descending
 - Ignore subsequent frames

 Camera Angle

 - Side view only (perpendicular to lifter)

 ---
 Phase Structure (User Decision)

 4 Phases - Quarters of the vertical wrist range:
 - Phase 1 (0-25%): Floor to quarter height
 - Phase 2 (25-50%): Quarter to halfway
 - Phase 3 (50-75%): Halfway to three-quarters
 - Phase 4 (75-100%): Three-quarters to lockout

 Metrics to Check Per Phase

 1. Back Angle (from horizontal)

 - Draw horizontal line through hip point
 - Measure angle from horizontal to hip-shoulder line
 - 0° = back horizontal, 90° = back vertical (upright)
 - At lockout: should be ~90° (standing upright)
 - At floor: typically 30-50° depending on build

 2. Thigh Angle (from horizontal) - NEW

 - Draw horizontal line through hip point
 - Measure angle from horizontal to hip-knee line
 - 0° = thigh horizontal, 90° = thigh vertical (standing)
 - Useful for tracking hip height relative to knees

 3. Hip Angle (joint angle)

 - Angle at hip joint (shoulder-hip-knee)
 - 180° = fully extended, smaller = more bent
 - This is the angle BETWEEN back and thigh

 4. Knee Angle

 - Angle at knee joint (hip-knee-ankle)
 - 180° = fully extended, smaller = more bent

 5. Bar Path Drift

 - Horizontal deviation from starting X position
 - Measured as percentage of body width or absolute pixels

 6. Shoulder Position Relative to Bar (NEW)

 - Horizontal relationship between shoulder X and wrist X (bar position)
 - Shoulder behind bar: shoulder_x > wrist_x (leaning back)
 - Shoulder over bar: shoulder_x ≈ wrist_x (ideal setup for conventional)
 - Shoulder in front of bar: shoulder_x < wrist_x (common at start)
 - Measured as: (shoulder_x - wrist_x) / body_width * 100 (percentage)
 - Negative = in front, Positive = behind, ~0 = over

 7. Wrist-to-Leg Distance (NEW)

 - Horizontal distance between wrist and leg line
 - Lower phases (1-2): Distance to shin line (ankle-knee)
 - Upper phases (3-4): Distance to thigh line (knee-hip)
 - Smaller = bar closer to body (generally better)
 - Can detect bar drifting away from legs

 Calculation for Wrist-to-Leg Distance:

 # For shin (lower phases):
 shin_x_at_wrist_y = interpolate(ankle_x, knee_x, wrist_y)
 distance = abs(wrist_x - shin_x_at_wrist_y)

 # For thigh (upper phases):
 thigh_x_at_wrist_y = interpolate(knee_x, hip_x, wrist_y)
 distance = abs(wrist_x - thigh_x_at_wrist_y)

 ---
 Default Thresholds Per Phase

 Scoring: Start at 100, deduct points for violations

 Angle Reference:
 - Back Angle: measured from horizontal through hips (0° = horizontal, 90° = upright)
 - Thigh Angle: measured from horizontal through hips (0° = horizontal, 90° = vertical/standing)

 Phase 1 (0-25%): Floor to Quarter Height
 ┌──────────────────────────┬─────────────┬───────────────────┬─────────────────────┐
 │          Metric          │ Ideal Range │   Minor Penalty   │    Major Penalty    │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Back Angle (from horiz)  │ 30-50°      │ 25-55° (-5)       │ <25° or >55° (-15)  │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Thigh Angle (from horiz) │ 30-50°      │ 25-55° (-5)       │ <25° or >55° (-10)  │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Hip Angle (joint)        │ 70-90°      │ 60-100° (-5)      │ <60° or >100° (-15) │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Knee Angle               │ 90-120°     │ 80-130° (-5)      │ <80° or >130° (-10) │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Shoulder Position        │ -5% to +5%  │ -10% to +10% (-5) │ outside ±10% (-15)  │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Bar Drift                │ <3%         │ 3-6% (-5)         │ >6% (-15)           │
 ├──────────────────────────┼─────────────┼───────────────────┼─────────────────────┤
 │ Wrist-to-Shin            │ <4%         │ 4-8% (-5)         │ >8% (-15)           │
 └──────────────────────────┴─────────────┴───────────────────┴─────────────────────┘
 Phase 2 (25-50%): Quarter to Halfway
 ┌──────────────────────────┬─────────────┬──────────────────┬──────────────────────┐
 │          Metric          │ Ideal Range │  Minor Penalty   │    Major Penalty     │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Back Angle (from horiz)  │ 40-55°      │ 35-60° (-5)      │ <35° or >60° (-15)   │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Thigh Angle (from horiz) │ 45-65°      │ 40-70° (-5)      │ <40° or >70° (-10)   │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Hip Angle (joint)        │ 90-120°     │ 80-130° (-5)     │ <80° or >130° (-15)  │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Knee Angle               │ 120-150°    │ 110-160° (-5)    │ <110° or >160° (-10) │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Shoulder Position        │ -3% to +8%  │ -8% to +12% (-5) │ outside (-15)        │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Bar Drift                │ <4%         │ 4-7% (-5)        │ >7% (-15)            │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Wrist-to-Shin            │ <4%         │ 4-8% (-5)        │ >8% (-15)            │
 └──────────────────────────┴─────────────┴──────────────────┴──────────────────────┘
 Phase 3 (50-75%): Halfway to Three-Quarters
 ┌──────────────────────────┬─────────────┬──────────────────┬──────────────────────┐
 │          Metric          │ Ideal Range │  Minor Penalty   │    Major Penalty     │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Back Angle (from horiz)  │ 55-75°      │ 50-80° (-5)      │ <50° or >80° (-15)   │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Thigh Angle (from horiz) │ 65-80°      │ 60-85° (-5)      │ <60° or >85° (-10)   │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Hip Angle (joint)        │ 130-160°    │ 120-165° (-5)    │ <120° or >165° (-15) │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Knee Angle               │ 150-170°    │ 140-175° (-5)    │ <140° (-10)          │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Shoulder Position        │ 0% to +10%  │ -5% to +15% (-5) │ outside (-15)        │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Bar Drift                │ <5%         │ 5-8% (-5)        │ >8% (-15)            │
 ├──────────────────────────┼─────────────┼──────────────────┼──────────────────────┤
 │ Wrist-to-Thigh           │ <3%         │ 3-6% (-5)        │ >6% (-15)            │
 └──────────────────────────┴─────────────┴──────────────────┴──────────────────────┘
 Phase 4 (75-100%): Three-Quarters to Lockout
 ┌──────────────────────────┬─────────────┬─────────────────┬───────────────┐
 │          Metric          │ Ideal Range │  Minor Penalty  │ Major Penalty │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Back Angle (from horiz)  │ 80-90°      │ 75-90° (-5)     │ <75° (-20)    │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Thigh Angle (from horiz) │ 80-90°      │ 75-90° (-5)     │ <75° (-15)    │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Hip Angle (joint)        │ 165-180°    │ 155-180° (-5)   │ <155° (-20)   │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Knee Angle               │ 170-180°    │ 160-180° (-5)   │ <160° (-15)   │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Shoulder Position        │ +5% to +15% │ 0% to +20% (-5) │ outside (-15) │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Bar Drift                │ <5%         │ 5-8% (-5)       │ >8% (-15)     │
 ├──────────────────────────┼─────────────┼─────────────────┼───────────────┤
 │ Wrist-to-Thigh           │ <3%         │ 3-6% (-5)       │ >6% (-10)     │
 └──────────────────────────┴─────────────┴─────────────────┴───────────────┘
 Note: These are starting defaults. All thresholds will be configurable.

 ---
 Limitations

 1. No Z-depth: Can't detect if bar drifts forward/back from side view perspective
 2. Camera angle dependent: Analysis assumes side view
 3. Single person: Multi-person not supported
 4. Occlusion: Plates may block knees/ankles (mitigated by smoothing)

 ---
 Implementation Plan

 Files to Modify

 1. apps/api/src/core/analyzers/deadlift_analyzer.py
   - Rewrite analyze() method with phase-based approach
   - Add phase detection using wrist vertical range
   - Add new metric calculations (knee angle, wrist-to-leg distance)
   - Implement deduction-based scoring
 2. apps/api/src/core/angle_calculator.py
   - Add calculate_angle_from_horizontal(point_a, point_b) function
       - Returns angle in degrees from horizontal line through point_a to the line point_a→point_b
     - Used for: back angle (hip→shoulder), thigh angle (hip→knee)
   - Add calculate_knee_angle(hip, knee, ankle) function
   - Add calculate_wrist_to_leg_distance(wrist, leg_top, leg_bottom) function
   - Add calculate_shoulder_bar_position(shoulder, wrist, body_width) function
       - Returns percentage: negative = in front, positive = behind, 0 = over bar
 3. apps/api/src/core/analyzers/base_analyzer.py (if needed)
   - Add shared phase detection utilities

 New Data Structures

 # Phase thresholds config (can be moved to config file later)
 DEADLIFT_PHASE_THRESHOLDS = {
     "phase_1": {
         "back_angle": {"ideal": (40, 55), "minor": (35, 60), "major_penalty": 15},
         "hip_angle": {"ideal": (70, 90), "minor": (60, 100), "major_penalty": 15},
         # ... etc
     },
     # ... phases 2-4
 }

 # Output structure per phase
 {
     "phase": 1,
     "frame_range": [0, 25],
     "metrics": {
         "back_angle": {"value": 48, "status": "ideal"},
         "hip_angle": {"value": 85, "status": "ideal"},
         # ...
     },
     "deductions": 0
 }

 Implementation Steps

 1. Phase Detection
   - Find min/max wrist Y across all frames
   - Calculate vertical range
   - Assign each frame to a phase (1-4) based on wrist Y position
   - Detect first rep completion (wrist reaches max and starts descending)
 2. Metric Calculation Per Frame
   - Calculate all 7 metrics for each frame:
       i. Back angle (from horizontal)
     ii. Thigh angle (from horizontal)
     iii. Hip joint angle
     iv. Knee joint angle
     v. Bar drift
     vi. Shoulder position relative to bar
     vii. Wrist-to-leg distance
   - Store with frame number and phase assignment
 3. Phase Scoring
   - For each phase, take the average (or worst) value of each metric
   - Apply deductions based on threshold violations
   - Sum deductions across all phases
 4. Issue Generation
   - Generate specific issues with phase context
   - e.g., "Excessive forward lean in Phase 2 (back angle 62°)"

 ---
 Verification

 1. Run existing tests to ensure no regressions
 2. Test with sample deadlift video:
   - Verify phase detection splits lift into 4 parts
   - Verify first rep detection works (stops at lockout)
   - Verify all 7 metrics calculated for each phase
   - Verify deductions applied correctly
   - Verify issues include phase context
 3. Compare output structure with frontend expectations