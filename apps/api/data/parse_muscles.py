#!/usr/bin/env python3
"""
Parse all EMG research files and generate exercise_muscles.json.

Reads:
  - research/*.md (chest, back, shoulders, arms, quads_calves, hams_glutes, core, fullbody_misc)
  - ../../context/EXERCISE-RESEARCH.md (manually verified, takes precedence)
  - EXERCISE-LIST-400.md (canonical exercise names, 1-385)

Outputs:
  - exercise_muscles.json
"""

import json
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(SCRIPT_DIR, "research")
EXERCISE_RESEARCH_PATH = os.path.join(SCRIPT_DIR, "..", "..", "..", "context", "EXERCISE-RESEARCH.md")
EXERCISE_LIST_PATH = os.path.join(SCRIPT_DIR, "EXERCISE-LIST-400.md")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "exercise_muscles.json")

VALID_MUSCLE_GROUPS = {
    "Upper Chest", "Mid Chest", "Lower Chest",
    "Upper Lats", "Lower Lats",
    "Upper Traps", "Mid Traps", "Lower Traps",
    "Erector Spinae",
    "Front Delts", "Lateral Delts", "Rear Delts",
    "Biceps Long Head", "Biceps Short Head",
    "Brachialis", "Brachioradialis",
    "Triceps Lateral & Medial", "Triceps Long Head",
    "Forearm Flexors", "Forearm Extensors",
    "Pronators & Supinators",
    "Vastus Group", "Rectus Femoris",
    "Hip Extensors", "Knee Flexors",
    "Gluteus Maximus", "Gluteus Medius & Minimus",
    "Gastrocnemius", "Soleus", "Tibialis Anterior",
    "Upper Abs", "Lower Abs", "Obliques",
    "Hip Adductors", "Neck", "Rotator Cuff",
}

VALID_ACTIVATIONS = {"maximum", "high", "medium", "partial"}

# Headers/sections to skip (not exercises)
SKIP_HEADERS = {
    "cross-exercise consistency notes",
    "lat activation hierarchy",
    "biceps activation",
    "erector spinae",
    "rear delt isolation hierarchy",
    "unilateral anti-rotation effect",
    "previously researched",
    "calibration references",
    "calibration",
    "quad exercises",
    "calf exercises",
    "summary of key emg principles applied",
    "quadriceps distinctions",
    "calf distinctions",
    "machine vs free weight",
    "summary",
    "hamstring exercises",
    "glute exercises",
    "adductor exercises",
    "key emg research sources",
    "biceps exercises",
    "triceps exercises",
    "forearm exercises",
    "upper abs / flexion",
    "lower abs / hip flexion",
    "obliques / rotation",
    "anti-extension / stability",
    "deadlift variants",
    "olympic lifts",
    "functional/strongman",
    "kettlebell exercises",
    "plyometrics",
    "cardio/conditioning",
    "stretching/mobility",
    "band exercises",
    "additional popular",
    "rotator cuff exercises",
    "neck exercises",
    "completed research",
    "remaining",
    "exercises still needing research from current 137",
    "new exercises to add",
    "summary statistics",
    "notes on calibration consistency",
    "status",
    "sources",
    # Calibration lines that look like headers
    "chest exercises - emg-backed muscle activation mappings",
    "back exercises - emg-backed muscle activation research",
    "shoulder, rotator cuff & neck exercises - emg-backed muscle activation mappings",
    "arms exercise research: emg-backed muscle activation mappings",
    "quad & calf exercises — emg-backed muscle activation mappings",
    "hamstring, glute & adductor exercise muscle activation research (emg-backed)",
    "core exercises - emg-backed muscle activation mappings",
    "full body compounds, kettlebell, plyometrics, cardio, stretching & band exercises — emg-backed muscle mappings",
    "exercise muscle activation research (emg-backed)",
}


def parse_exercise_list(filepath):
    """Parse EXERCISE-LIST-400.md to get canonical exercise names and their numbers."""
    exercises = {}
    with open(filepath, 'r') as f:
        content = f.read()

    # Match lines like: "1. Barbell Bench Press [EXISTING]" or "5. Floor Press"
    # Capture everything after the number up to [EXISTING] or end of line
    pattern = re.compile(r'^\s*(\d+)\.\s+(.+?)(?:\s+\[EXISTING\])?\s*$', re.MULTILINE)
    for m in pattern.finditer(content):
        num = int(m.group(1))
        name = m.group(2).strip()
        # Clean up parenthetical notes in the name that are NOT part of the exercise name
        # e.g. "Chin-Up Curl (Supinated narrow grip, listed under Back too)" -> "Chin-Up Curl"
        # But keep parentheticals that ARE part of the exercise name
        # e.g. "Tricep Pushdown (Rope)", "Hip Hinge (Band)", "Ab Wheel (Kneeling)"
        paren_match = re.match(r'^(.+?)\s+\((.+)\)\s*$', name)
        if paren_match:
            paren_text = paren_match.group(2).strip()
            # Only strip if it's a descriptive note, not a variant name
            if any(kw in paren_text.lower() for kw in ['listed under', 'supinated narrow grip',
                                                         'close-grip db press variation']):
                name = paren_match.group(1).strip()
            # else keep the full name with parens
        exercises[num] = name

    return exercises


def clean_exercise_name(raw_name):
    """Clean up an exercise name from a research file header."""
    # Remove leading numbers like "1. ", "## 1. ", "### 28. "
    name = re.sub(r'^\d+\.\s*', '', raw_name)
    # Remove markdown header markers
    name = name.strip('#').strip()
    # Remove trailing notes in parens that are descriptive, not part of name
    # But be careful: some exercises have parens as part of their name
    name = name.strip()
    # Remove asterisks
    name = name.replace('*', '')
    # Remove trailing colons
    name = name.rstrip(':')
    name = name.strip()
    return name


def parse_muscle_table(lines, start_idx):
    """Parse a markdown table of muscle activations starting at start_idx.
    Returns (muscles_list, end_idx)."""
    muscles = []
    i = start_idx

    # Find the table header row (contains "Muscle" and "Activation")
    while i < len(lines):
        line = lines[i].strip()
        if '|' in line and ('muscle' in line.lower() or 'activation' in line.lower()):
            i += 1  # skip header
            break
        elif line.startswith('|') and '---' in line:
            # We're at the separator, the previous line was the header
            i += 1  # skip separator
            break
        elif '|' in line and '---' in line:
            i += 1
            break
        i += 1

    # Skip separator row if we haven't already
    if i < len(lines) and '---' in lines[i]:
        i += 1

    # Parse data rows
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith('|') or line == '':
            break
        if '---' in line:
            i += 1
            continue

        # Parse: | Muscle Group | Activation | or | Muscle | Activation | Notes |
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]  # remove empty from leading/trailing |

        if len(parts) >= 2:
            muscle = parts[0].strip()
            activation = parts[1].strip().lower()

            # Normalize muscle names
            muscle = muscle.replace('Muscle Group', '').replace('Muscle', '').strip()
            if not muscle or muscle.lower() in ('muscle group', 'muscle', ''):
                i += 1
                continue

            if activation in VALID_ACTIVATIONS and muscle in VALID_MUSCLE_GROUPS:
                muscles.append({
                    "muscle_group": muscle,
                    "activation_level": activation
                })
            elif muscle not in VALID_MUSCLE_GROUPS and muscle and activation in VALID_ACTIVATIONS:
                print(f"  WARNING: Unknown muscle group '{muscle}' with activation '{activation}'")

        i += 1

    return muscles, i


def parse_research_file(filepath):
    """Parse a research .md file and return a dict of exercise_name -> muscles."""
    exercises = {}

    with open(filepath, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect exercise headers: ## Exercise, ### Exercise, ## 1. Exercise, ### 1. Exercise
        header_match = re.match(r'^(#{2,3})\s+(?:\d+\.\s+)?(.+)$', line)

        if header_match:
            raw_name = header_match.group(2).strip()
            clean_name = clean_exercise_name(raw_name)

            # Skip non-exercise headers
            if clean_name.lower() in SKIP_HEADERS:
                i += 1
                continue

            # Skip "see existing research" references
            if '(see existing research' in line.lower() or 'see existing research' in raw_name.lower():
                i += 1
                continue

            # Skip if this is a section header (all caps typically)
            if clean_name.upper() == clean_name and len(clean_name) > 3 and not any(c.isdigit() for c in clean_name):
                if clean_name not in VALID_MUSCLE_GROUPS:
                    i += 1
                    continue

            # Look ahead for a table
            j = i + 1
            found_table = False
            while j < len(lines) and j < i + 20:  # look max 20 lines ahead
                if lines[j].strip().startswith('|') and ('muscle' in lines[j].lower() or 'activation' in lines[j].lower() or '---' in lines[j]):
                    muscles, end_idx = parse_muscle_table(lines, j)
                    if muscles:
                        exercises[clean_name] = muscles
                        found_table = True
                        i = end_idx
                        break
                elif lines[j].strip().startswith('#'):
                    break  # Next header, stop looking
                j += 1

            if not found_table:
                i += 1
        else:
            i += 1

    return exercises


def parse_exercise_research_md(filepath):
    """Parse EXERCISE-RESEARCH.md — has a slightly different format with some entries as
    'Exercise — CONFIRMED CORRECT' and 'Proposed mapping'."""
    exercises = {}

    with open(filepath, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect exercise headers
        header_match = re.match(r'^(#{2,3})\s+(?:\d+\.\s+)?(.+)$', line)

        if header_match:
            raw_name = header_match.group(2).strip()

            # Handle "Wrist Curl — CONFIRMED CORRECT" style
            confirmed_match = re.match(r'^(.+?)\s*[—–-]+\s*CONFIRMED\s+CORRECT\s*$', raw_name)
            if confirmed_match:
                raw_name = confirmed_match.group(1).strip()

            clean_name = clean_exercise_name(raw_name)

            # Skip non-exercise headers
            if clean_name.lower() in SKIP_HEADERS:
                i += 1
                continue

            # Skip "see existing research" references
            if 'see existing research' in line.lower():
                i += 1
                continue

            # Skip section-only headers
            skip_keywords = ['remaining', 'exercises still needing', 'new exercises',
                           'no "maximum"', 'have "maximum"']
            if any(kw in clean_name.lower() for kw in skip_keywords):
                i += 1
                continue

            # Look ahead for a table
            j = i + 1
            found_table = False
            while j < len(lines) and j < i + 20:
                if lines[j].strip().startswith('|') and ('muscle' in lines[j].lower() or 'activation' in lines[j].lower() or '---' in lines[j]):
                    muscles, end_idx = parse_muscle_table(lines, j)
                    if muscles:
                        exercises[clean_name] = muscles
                        found_table = True
                        i = end_idx
                        break
                elif lines[j].strip().startswith('#'):
                    break
                j += 1

            if not found_table:
                i += 1
        else:
            i += 1

    return exercises


def parse_calibration_references(filepath):
    """Parse calibration reference lines at the top of some files.
    Format: **Exercise Name**: Muscle=activation, Muscle=activation, ..."""
    exercises = {}

    with open(filepath, 'r') as f:
        content = f.read()

    # Match calibration lines like: **Goblet Squat**: Vastus Group=maximum, ...
    pattern = re.compile(r'\*\*(.+?)\*\*:\s*(.+?)(?:\n|$)')
    for m in pattern.finditer(content):
        name = m.group(1).strip()
        mappings_str = m.group(2).strip()

        muscles = []
        for pair in mappings_str.split(','):
            pair = pair.strip()
            if '=' in pair:
                muscle, activation = pair.rsplit('=', 1)
                muscle = muscle.strip()
                activation = activation.strip().lower()
                if muscle in VALID_MUSCLE_GROUPS and activation in VALID_ACTIVATIONS:
                    muscles.append({
                        "muscle_group": muscle,
                        "activation_level": activation
                    })

        if muscles:
            exercises[name] = muscles

    return exercises


def build_name_mapping(canonical_exercises):
    """Build a mapping from various name variants to canonical names."""
    mapping = {}

    # Direct name mapping
    for num, name in canonical_exercises.items():
        mapping[name.lower()] = name

    # Known name variants (research file name -> canonical name)
    variants = {
        "chest supported dumbbell row": "Chest-Supported Dumbbell Row",
        "chest-supported dumbbell row": "Chest-Supported Dumbbell Row",
        "chest supported machine row": "Chest-Supported Machine Row",
        "chest-supported machine row": "Chest-Supported Machine Row",
        "deadlift (conventional)": "Deadlift",
        "deadlift": "Deadlift",
        "thruster (barbell)": "Thruster",
        "thruster": "Thruster",
        "sled pull (backward)": "Sled Pull",
        "sled pull": "Sled Pull",
        "sled drag (forward, backward walk)": "Sled Drag",
        "sled drag": "Sled Drag",
        "jump squat": "Jump Squat",  # in quads_calves as quad exercise, in plyometrics as #40
        "box jump (step down)": "Box Jump (Step Down)",
        "lat pulldown (close grip)": "Lat Pulldown (Close Grip)",
        "cable lateral pulldown": "Cable Lateral Pulldown",
        "glute bridge (bodyweight)": "Glute Bridge",
        "glute bridge": "Glute Bridge",
        "hip hinge (band)": "Hip Hinge (Band)",
        "kettlebell swing": "Double Kettlebell Swing",  # There's no single KB swing in the list; but Double is #315
        "chin-up curl": "Chin-Up Curl",
        "chin-up curl (supinated narrow grip, listed under back too)": "Chin-Up Curl",
        "body drag curl": "Body Drag Curl",
        "ab wheel (kneeling)": "Ab Wheel (Kneeling)",
        "cable hip kickback": "Cable Hip Extension",
        # NOTE: "Cable Kickback" in research/*.md is the TRICEPS exercise (#138 Cable Kickback)
        # "Cable Kickback" in EXERCISE-RESEARCH.md is actually the GLUTE exercise (#216 Cable Hip Extension)
        # We handle this conflict in the special resolution code below
        "lateral raise (cable, behind back)": "Lateral Raise (Cable, Behind Back)",
        "behind-the-neck lat pulldown": "Behind-the-Neck Lat Pulldown",
        "prone row": "Prone Row",
        "viking press": "Viking Press",
        "smith machine shoulder press": "Smith Machine Shoulder Press",
        "ez-bar preacher curl": "EZ-Bar Preacher Curl",
        "cable concentration curl": "Cable Concentration Curl",
        "french press (ez-bar)": "French Press (EZ-Bar)",
        "jefferson squat": "Jefferson Squat",
        "hatfield squat": "Hatfield Squat",
        "atg split squat": "ATG Split Squat",
        "poliquin step-up": "Poliquin Step-Up",
        "man maker": "Man Maker",
        "devil press": "Devil Press",
        "sandbag clean": "Sandbag Clean",
        "rope climb": "Rope Climb",
        "prowler push": "Prowler Push",
        "sledgehammer swing": "Sledgehammer Swing",
        "hanging windshield wiper": "Hanging Windshield Wiper",
        "dumbbell squeeze press": "Dumbbell Squeeze Press",
        "21s (barbell curl)": "21s (Barbell Curl)",
        "sled leg press (vertical)": "Sled Leg Press (Vertical)",
        "45-degree hip extension": "45-Degree Hip Extension",
        "45-degree back extension": "45-Degree Back Extension",
        "banded hip thrust": "Banded Hip Thrust",
        "smith machine lunge": "Smith Machine Lunge",
        "dragon flag": "Dragon Flag",
        "l-sit": "L-Sit",
        "suitcase carry": "Suitcase Carry",
        "ab wheel": "Ab Wheel (Kneeling)",
        "ab wheel (kneeling)": "Ab Wheel (Kneeling)",
        "jump rope calf bounce": "Jump Rope Calf Bounce",
        "calf raise (bodyweight)": "Calf Raise (Bodyweight)",
        "calf raise": "Calf Raise (Bodyweight)",
        "lat pulldown (close grip)": "Lat Pulldown (Close Grip)",
        "hip hinge (band)": "Hip Hinge (Band)",
        "hip hinge": "Hip Hinge (Band)",
        "sled leg press (vertical)": "Sled Leg Press (Vertical)",
        "sled leg press": "Sled Leg Press (Vertical)",
        "21s (barbell curl)": "21s (Barbell Curl)",
        "21s": "21s (Barbell Curl)",
        "french press (ez-bar)": "French Press (EZ-Bar)",
        "french press": "French Press (EZ-Bar)",
        "dumbbell squeeze press (close-grip db press variation)": "Dumbbell Squeeze Press",
        "dumbbell squeeze press": "Dumbbell Squeeze Press",
    }

    for variant, canonical in variants.items():
        mapping[variant.lower()] = canonical

    return mapping


def find_canonical_name(research_name, name_mapping, canonical_names_set):
    """Try to find the canonical name for a research file exercise name."""
    # Direct match
    if research_name in canonical_names_set:
        return research_name

    # Case-insensitive match via mapping
    lower = research_name.lower()
    if lower in name_mapping:
        return name_mapping[lower]

    # Try without parenthetical
    no_paren = re.sub(r'\s*\(.*?\)\s*$', '', research_name).strip()
    if no_paren in canonical_names_set:
        return no_paren
    if no_paren.lower() in name_mapping:
        return name_mapping[no_paren.lower()]

    return None


def main():
    # 1. Parse canonical exercise list
    canonical_exercises = parse_exercise_list(EXERCISE_LIST_PATH)
    canonical_names_set = set(canonical_exercises.values())
    print(f"Canonical exercises: {len(canonical_exercises)} (expected 385)")

    # 2. Build name mapping
    name_mapping = build_name_mapping(canonical_exercises)

    # 3. Parse all research files
    all_research = {}

    research_files = [
        "chest.md", "back.md", "shoulders.md", "arms.md",
        "quads_calves.md", "hams_glutes.md", "core.md", "fullbody_misc.md"
    ]

    for fname in research_files:
        fpath = os.path.join(RESEARCH_DIR, fname)
        if os.path.exists(fpath):
            exercises = parse_research_file(fpath)
            # Also try calibration references
            calibration = parse_calibration_references(fpath)
            print(f"  {fname}: {len(exercises)} exercises, {len(calibration)} calibration refs")

            for name, muscles in {**calibration, **exercises}.items():
                canonical = find_canonical_name(name, name_mapping, canonical_names_set)
                if canonical:
                    all_research[canonical] = muscles
                else:
                    print(f"  WARNING: Could not match '{name}' from {fname}")

    print(f"\nTotal from research/*.md: {len(all_research)}")

    # 4. Parse EXERCISE-RESEARCH.md (takes precedence)
    exercise_research = parse_exercise_research_md(EXERCISE_RESEARCH_PATH)
    calibration_er = parse_calibration_references(EXERCISE_RESEARCH_PATH)
    exercise_research.update(calibration_er)
    print(f"EXERCISE-RESEARCH.md: {len(exercise_research)} exercises")

    er_matched = 0
    for name, muscles in exercise_research.items():
        # Special case: "Cable Kickback" in EXERCISE-RESEARCH.md is the GLUTE exercise
        # (Cable Hip Extension #216), NOT the triceps Cable Kickback (#138)
        if name == "Cable Kickback":
            all_research["Cable Hip Extension"] = muscles
            er_matched += 1
            continue

        canonical = find_canonical_name(name, name_mapping, canonical_names_set)
        if canonical:
            all_research[canonical] = muscles  # Override with verified version
            er_matched += 1
        else:
            print(f"  WARNING: Could not match '{name}' from EXERCISE-RESEARCH.md")
    print(f"  Matched: {er_matched}")

    print(f"\nTotal after merge: {len(all_research)}")

    # 5. Handle special cases and duplicates
    # "Cable Kickback" appears in both arms.md (triceps exercise) and EXERCISE-RESEARCH.md (glute exercise)
    # The triceps Cable Kickback from arms.md is exercise #138 in the list
    # The glute Cable Kickback from EXERCISE-RESEARCH.md is actually "Cable Hip Extension" (#216)
    # We need to make sure they don't conflict

    # Handle Kettlebell Swing - it's in fullbody_misc.md as #27 but the canonical list only has
    # "Double Kettlebell Swing" (#315). The single KB swing research maps to Double KB Swing.
    # Actually, fullbody_misc.md has BOTH #27 (Kettlebell Swing) and #36 (Double Kettlebell Swing).
    # The exercise list doesn't have a single KB swing - let's check...
    # Looking at the exercise list: no single KB swing. So #27's data should not override #36.

    # 6. Check for exercises in the canonical list that are still missing
    missing = []
    for num, name in sorted(canonical_exercises.items()):
        if name not in all_research:
            missing.append((num, name))

    print(f"\nMissing exercises: {len(missing)}")
    for num, name in missing:
        print(f"  {num}. {name}")

    # 7. Generate mappings for missing exercises based on similar exercises
    missing_mappings = generate_missing_mappings(missing, all_research)
    for name, muscles in missing_mappings.items():
        all_research[name] = muscles

    print(f"\nAfter filling missing: {len(all_research)}")

    # Final check
    still_missing = []
    for num, name in sorted(canonical_exercises.items()):
        if name not in all_research:
            still_missing.append((num, name))

    if still_missing:
        print(f"\nSTILL MISSING: {len(still_missing)}")
        for num, name in still_missing:
            print(f"  {num}. {name}")

    # 8. Build output
    output = []
    for num, name in sorted(canonical_exercises.items()):
        if name in all_research:
            entry = {
                "exercise": name,
                "muscles": all_research[name]
            }
            output.append(entry)
        else:
            print(f"ERROR: No mapping for #{num} '{name}'")

    # Validate
    print(f"\nOutput: {len(output)} exercises")
    for entry in output:
        for m in entry["muscles"]:
            if m["muscle_group"] not in VALID_MUSCLE_GROUPS:
                print(f"  INVALID muscle: {m['muscle_group']} in {entry['exercise']}")
            if m["activation_level"] not in VALID_ACTIVATIONS:
                print(f"  INVALID activation: {m['activation_level']} in {entry['exercise']}")

    # Write output
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(output)} exercises to {OUTPUT_PATH}")


def generate_missing_mappings(missing_exercises, existing_research):
    """Generate muscle activation mappings for exercises not found in research files.
    Uses biomechanical similarity to existing exercises."""

    mappings = {}

    for num, name in missing_exercises:
        muscles = None

        # --- SPECIAL CASES ---

        # Exercises that reference existing patterns
        if name == "Chin-Up Curl":
            # Similar to chin-up but more biceps emphasis
            muscles = [
                {"muscle_group": "Biceps Short Head", "activation_level": "maximum"},
                {"muscle_group": "Biceps Long Head", "activation_level": "maximum"},
                {"muscle_group": "Brachialis", "activation_level": "high"},
                {"muscle_group": "Upper Lats", "activation_level": "high"},
                {"muscle_group": "Lower Lats", "activation_level": "high"},
                {"muscle_group": "Brachioradialis", "activation_level": "medium"},
                {"muscle_group": "Lower Traps", "activation_level": "medium"},
                {"muscle_group": "Mid Traps", "activation_level": "medium"},
                {"muscle_group": "Forearm Flexors", "activation_level": "medium"},
                {"muscle_group": "Rear Delts", "activation_level": "partial"},
            ]
        elif name == "Body Drag Curl":
            # Similar to drag curl but bodyweight
            muscles = [
                {"muscle_group": "Biceps Long Head", "activation_level": "high"},
                {"muscle_group": "Biceps Short Head", "activation_level": "high"},
                {"muscle_group": "Brachialis", "activation_level": "medium"},
                {"muscle_group": "Brachioradialis", "activation_level": "medium"},
                {"muscle_group": "Forearm Flexors", "activation_level": "medium"},
            ]
        elif name == "Dumbbell Squeeze Press":
            # Already in chest.md as "Squeeze Press"
            if "Squeeze Press" in existing_research:
                muscles = existing_research["Squeeze Press"]
        elif name == "Hip Hinge (Band)":
            # Similar to banded good morning
            muscles = [
                {"muscle_group": "Hip Extensors", "activation_level": "high"},
                {"muscle_group": "Erector Spinae", "activation_level": "high"},
                {"muscle_group": "Knee Flexors", "activation_level": "medium"},
                {"muscle_group": "Gluteus Maximus", "activation_level": "medium"},
            ]
        elif name == "Sled Leg Press (Vertical)":
            # Similar to leg press
            muscles = [
                {"muscle_group": "Vastus Group", "activation_level": "maximum"},
                {"muscle_group": "Rectus Femoris", "activation_level": "high"},
                {"muscle_group": "Gluteus Maximus", "activation_level": "medium"},
                {"muscle_group": "Hip Extensors", "activation_level": "medium"},
                {"muscle_group": "Knee Flexors", "activation_level": "medium"},
            ]
        elif name == "Jump Rope Calf Bounce":
            # Basically same as jump rope with calf emphasis
            muscles = [
                {"muscle_group": "Gastrocnemius", "activation_level": "high"},
                {"muscle_group": "Soleus", "activation_level": "high"},
                {"muscle_group": "Tibialis Anterior", "activation_level": "medium"},
                {"muscle_group": "Forearm Flexors", "activation_level": "medium"},
                {"muscle_group": "Forearm Extensors", "activation_level": "medium"},
                {"muscle_group": "Vastus Group", "activation_level": "partial"},
                {"muscle_group": "Rectus Femoris", "activation_level": "partial"},
                {"muscle_group": "Upper Abs", "activation_level": "partial"},
            ]
        elif name == "21s (Barbell Curl)":
            # Same as barbell curl but with partial ROM emphasis
            muscles = [
                {"muscle_group": "Biceps Short Head", "activation_level": "maximum"},
                {"muscle_group": "Biceps Long Head", "activation_level": "maximum"},
                {"muscle_group": "Brachialis", "activation_level": "high"},
                {"muscle_group": "Brachioradialis", "activation_level": "medium"},
                {"muscle_group": "Forearm Flexors", "activation_level": "medium"},
            ]
        elif name == "Wrist Curl":
            muscles = [
                {"muscle_group": "Forearm Flexors", "activation_level": "maximum"},
            ]
        elif name == "Reverse Wrist Curl":
            muscles = [
                {"muscle_group": "Forearm Extensors", "activation_level": "maximum"},
            ]
        elif name == "Barbell Lunge":
            if "Barbell Lunge" in existing_research:
                muscles = existing_research["Barbell Lunge"]
        elif name == "Walking Lunge":
            if "Walking Lunge" in existing_research:
                muscles = existing_research["Walking Lunge"]
        elif name == "Cable Lateral Pulldown":
            if "Cable Lateral Pulldown" in existing_research:
                muscles = existing_research["Cable Lateral Pulldown"]
        elif name == "Cable Kickback" and "Cable Kickback" in existing_research:
            # Triceps cable kickback (from arms.md)
            muscles = existing_research["Cable Kickback"]
        elif name == "Lat Pulldown (Close Grip)":
            # Similar to Lat Pulldown but close grip - emphasizes lats with more biceps
            if "Lat Pulldown" in existing_research:
                muscles = existing_research["Lat Pulldown"]
            else:
                muscles = [
                    {"muscle_group": "Upper Lats", "activation_level": "maximum"},
                    {"muscle_group": "Lower Lats", "activation_level": "maximum"},
                    {"muscle_group": "Biceps Short Head", "activation_level": "high"},
                    {"muscle_group": "Biceps Long Head", "activation_level": "high"},
                    {"muscle_group": "Lower Traps", "activation_level": "medium"},
                    {"muscle_group": "Mid Traps", "activation_level": "medium"},
                    {"muscle_group": "Rear Delts", "activation_level": "medium"},
                    {"muscle_group": "Brachialis", "activation_level": "medium"},
                    {"muscle_group": "Brachioradialis", "activation_level": "medium"},
                    {"muscle_group": "Forearm Flexors", "activation_level": "partial"},
                ]
        elif name == "Calf Raise (Bodyweight)":
            muscles = [
                {"muscle_group": "Gastrocnemius", "activation_level": "high"},
                {"muscle_group": "Soleus", "activation_level": "medium"},
                {"muscle_group": "Tibialis Anterior", "activation_level": "partial"},
            ]
        elif name == "French Press (EZ-Bar)":
            # Same as skull crusher - EZ-bar lying triceps extension
            muscles = [
                {"muscle_group": "Triceps Long Head", "activation_level": "maximum"},
                {"muscle_group": "Triceps Lateral & Medial", "activation_level": "high"},
                {"muscle_group": "Front Delts", "activation_level": "partial"},
                {"muscle_group": "Forearm Extensors", "activation_level": "partial"},
            ]
        elif name == "Ab Wheel (Kneeling)":
            # Same as Ab Rollout
            if "Ab Rollout" in existing_research:
                muscles = existing_research["Ab Rollout"]
            else:
                muscles = [
                    {"muscle_group": "Upper Abs", "activation_level": "maximum"},
                    {"muscle_group": "Lower Abs", "activation_level": "maximum"},
                    {"muscle_group": "Obliques", "activation_level": "high"},
                    {"muscle_group": "Erector Spinae", "activation_level": "medium"},
                    {"muscle_group": "Upper Lats", "activation_level": "partial"},
                    {"muscle_group": "Front Delts", "activation_level": "partial"},
                    {"muscle_group": "Triceps Lateral & Medial", "activation_level": "partial"},
                ]
        elif name == "Dumbbell Squeeze Press":
            # Close-grip DB press variation
            muscles = [
                {"muscle_group": "Mid Chest", "activation_level": "maximum"},
                {"muscle_group": "Upper Chest", "activation_level": "high"},
                {"muscle_group": "Triceps Lateral & Medial", "activation_level": "medium"},
                {"muscle_group": "Triceps Long Head", "activation_level": "medium"},
                {"muscle_group": "Front Delts", "activation_level": "medium"},
                {"muscle_group": "Forearm Flexors", "activation_level": "partial"},
            ]

        if muscles:
            mappings[name] = muscles

    return mappings


if __name__ == "__main__":
    main()
