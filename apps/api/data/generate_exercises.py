#!/usr/bin/env python3
"""
Generate exercises.json with all 385 exercises.
- Keeps existing 137 exercises exactly as-is
- Generates metadata for ~248 new exercises
- Cross-references free-exercise-db for instructions where available
- Output order matches EXERCISE-LIST-400.md numbering
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

DATA_DIR = Path(__file__).parent

# Load source data - get original exercises from git since the file may have been overwritten
import subprocess
result = subprocess.run(
    ['git', 'show', 'HEAD:apps/api/data/exercises.json'],
    capture_output=True, text=True,
    cwd=str(DATA_DIR.parent.parent.parent)  # repo root
)
if result.returncode == 0:
    existing_exercises = json.loads(result.stdout)
else:
    # Fall back to current file
    with open(DATA_DIR / "exercises.json") as f:
        existing_exercises = json.load(f)

with open(DATA_DIR / "free-exercise-db-exercises.json") as f:
    free_db = json.load(f)

with open(DATA_DIR / "EXERCISE-LIST-400.md") as f:
    exercise_list_md = f.read()

# Build lookup for existing exercises by name
existing_by_name = {e["name"]: e for e in existing_exercises}

# Build lookup for free-exercise-db by normalized name
def normalize(name):
    return re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()

free_db_by_norm = {}
for e in free_db:
    free_db_by_norm[normalize(e["name"])] = e

def fuzzy_match_free_db(name):
    """Try to find a matching exercise in free-exercise-db."""
    norm = normalize(name)

    # Exact match
    if norm in free_db_by_norm:
        return free_db_by_norm[norm]

    # Try common variations
    variations = [
        name,
        name.replace("Barbell ", "").replace("Dumbbell ", "").replace("Cable ", "").replace("Machine ", ""),
        name.replace("-", " "),
        name.replace("Fly", "Flye").replace("fly", "flye"),
    ]

    for var in variations:
        n = normalize(var)
        if n in free_db_by_norm:
            return free_db_by_norm[n]

    # Fuzzy match with threshold
    best_score = 0
    best_match = None
    for db_norm, db_entry in free_db_by_norm.items():
        score = SequenceMatcher(None, norm, db_norm).ratio()
        if score > best_score and score > 0.80:
            best_score = score
            best_match = db_entry

    return best_match

def clean_instructions(instructions):
    """Clean free-exercise-db instructions to be more concise."""
    cleaned = []
    for inst in instructions:
        # Remove "Tip:" sentences and "Repeat for..." endings
        inst = inst.strip()
        if inst.lower().startswith("repeat for") or inst.lower().startswith("repeat the movement"):
            continue
        # Remove "This will be your starting position." standalone
        if inst == "This will be your starting position.":
            continue
        # Shorten overly long instructions
        sentences = inst.split(". ")
        # Keep first 2-3 meaningful sentences
        meaningful = [s for s in sentences if not s.lower().startswith("tip:") and not s.lower().startswith("repeat")]
        if len(meaningful) > 3:
            meaningful = meaningful[:3]
        result = ". ".join(meaningful)
        if result and not result.endswith("."):
            result += "."
        if result:
            cleaned.append(result)
    # Limit to 5 steps max
    return cleaned[:5] if cleaned else None

# Parse the exercise list from MD
def parse_exercise_list(md_text):
    """Parse numbered exercises from EXERCISE-LIST-400.md, return list of (number, name, is_existing)."""
    exercises = []
    # Match lines like: "1. Barbell Bench Press [EXISTING]" or "5. Floor Press"
    pattern = r'^\s*(\d+)\.\s+(.+?)(?:\s+\[EXISTING\])?\s*$'

    for line in md_text.split('\n'):
        m = re.match(pattern, line)
        if m:
            num = int(m.group(1))
            # Clean the name - remove any parenthetical notes but keep the exercise name
            raw_name = m.group(2).strip()
            # Remove trailing parenthetical descriptions for clean name
            # But keep them for reference
            is_existing = '[EXISTING]' in line
            exercises.append((num, raw_name, is_existing))

    return exercises

exercise_list = parse_exercise_list(exercise_list_md)
print(f"Parsed {len(exercise_list)} exercises from EXERCISE-LIST-400.md")

# Verify we have 385
assert len(exercise_list) == 385, f"Expected 385 exercises, got {len(exercise_list)}"

# Now define metadata for all new exercises
# This is the core generation logic

def infer_equipment(name, section_context=""):
    name_l = name.lower()

    # Specific overrides FIRST (before generic keyword checks, to handle cases like
    # "Sled Leg Press" where "sled" would match "other" but it's actually a machine)
    specific_equipment = {
        "straight-arm pulldown": "cable",
        "single-arm lat pulldown": "cable",
        "wide-grip lat pulldown": "cable",
        "reverse-grip lat pulldown": "cable",
        "single-arm cable row": "cable",
        "overhead cable curl": "cable",
        "single-arm cable curl": "cable",
        "pulldown": "cable",
        "floor press": "barbell",
        "larsen press": "barbell",
        "push press": "barbell",
        "behind-the-neck press": "barbell",
        "bradford press": "barbell",
        "z press": "barbell",
        "drag curl": "barbell",
        "wide-grip barbell curl": "barbell",
        "skull crusher": "barbell",
        "floor skull crusher": "barbell",
        "jm press": "barbell",
        "overhead squat": "barbell",
        "stiff-leg deadlift": "barbell",
        "reverse lunge": "barbell",
        "deficit lunge": "barbell",
        "snatch": "barbell",
        "clean": "barbell",
        "hang clean": "barbell",
        "hang snatch": "barbell",
        "clean and jerk": "barbell",
        "push jerk": "barbell",
        "muscle snatch": "barbell",
        "jefferson deadlift": "barbell",
        "jefferson squat": "barbell",
        "hatfield squat": "barbell",
        "rack pull": "barbell",
        "behind-the-neck lat pulldown": "cable",
        "lateral raise (cable, behind back)": "cable",
        "21s (barbell curl)": "barbell",
        "ez-bar preacher curl": "barbell",
        "french press (ez-bar)": "barbell",
        "squeeze press": "dumbbell",
        "tate press": "dumbbell",
        "zottman curl": "dumbbell",
        "cross-body hammer curl": "dumbbell",
        "prone incline curl": "dumbbell",
        "single-arm dumbbell overhead extension": "dumbbell",
        "concentration curl": "dumbbell",
        "wrist roller": "other",
        "pronation/supination": "dumbbell",
        "finger curl": "barbell",
        "behind-the-back wrist curl": "barbell",
        "viking press": "other",
        "belt squat": "machine",
        "v-squat machine": "machine",
        "single-leg leg press": "machine",
        "single-leg leg curl": "machine",
        "chest-supported machine row": "machine",
        "assisted pull-up machine": "machine",
        "machine rear delt fly": "machine",
        "machine bicep curl": "machine",
        "machine tricep extension": "machine",
        "assisted dip machine": "machine",
        "machine crunch": "machine",
        "sled leg press (vertical)": "machine",
        "captain's chair leg raise": "machine",
        "ghd sit-up": "machine",
        "rowing machine": "machine",
        "assault bike": "machine",
        "ski erg": "machine",
        "stair climber": "machine",
        "reverse hyperextension": "machine",
        "45-degree back extension": "bodyweight",
        "45-degree hip extension": "bodyweight",
        "hip 90/90 stretch": "bodyweight",
        "world's greatest stretch": "bodyweight",
        "cat-cow": "bodyweight",
        "inverted row": "bodyweight",
        "neutral-grip pull-up": "bodyweight",
        "muscle-up": "bodyweight",
        "scapular pull-up": "bodyweight",
        "handstand push-up": "bodyweight",
        "pistol squat": "bodyweight",
        "bodyweight squat": "bodyweight",
        "jump squat": "bodyweight",
        "wall sit": "bodyweight",
        "cyclist squat": "bodyweight",
        "split squat": "bodyweight",
        "cossack squat": "bodyweight",
        "glute bridge": "bodyweight",
        "fire hydrant": "bodyweight",
        "frog pump": "bodyweight",
        "sliding leg curl": "bodyweight",
        "reverse nordic curl": "bodyweight",
        "bench dip": "bodyweight",
        "bodyweight tricep extension": "bodyweight",
        "chin-up curl": "bodyweight",
        "body drag curl": "bodyweight",
        "sit-up": "bodyweight",
        "v-up": "bodyweight",
        "lying leg raise": "bodyweight",
        "hanging knee raise": "bodyweight",
        "reverse crunch": "bodyweight",
        "flutter kick": "bodyweight",
        "scissor kick": "bodyweight",
        "oblique crunch": "bodyweight",
        "windshield wiper": "bodyweight",
        "hollow hold": "bodyweight",
        "body saw": "bodyweight",
        "bird dog": "bodyweight",
        "bear crawl": "bodyweight",
        "neck curl": "bodyweight",
        "neck extension": "bodyweight",
        "neck lateral flexion": "bodyweight",
        "dragon flag": "bodyweight",
        "l-sit": "bodyweight",
        "hanging windshield wiper": "bodyweight",
        "calf raise (bodyweight)": "bodyweight",
        "broad jump": "bodyweight",
        "depth jump": "bodyweight",
        "jump lunge": "bodyweight",
        "lateral bound": "bodyweight",
        "skater jump": "bodyweight",
        "tuck jump": "bodyweight",
        "single-leg box jump": "bodyweight",
        "hurdle hop": "bodyweight",
        "plyo push-up": "bodyweight",
        "jump rope": "other",
        "burpee": "bodyweight",
        "mountain climber": "bodyweight",
        "sprint": "bodyweight",
        "box jump (step down)": "bodyweight",
        "prone row": "dumbbell",
        "atg split squat": "bodyweight",
        "poliquin step-up": "bodyweight",
        "ab wheel (kneeling)": "other",
        "curtsy lunge": "bodyweight",
        "man maker": "dumbbell",
        "devil press": "dumbbell",
        "rope climb": "bodyweight",
        "neck harness extension": "other",
        "weighted crunch": "other",
        "weighted plank": "other",
        "stir the pot": "other",
        "spanish squat": "band",
        "plate front raise": "other",
        "bus driver": "other",
        "prone y raise": "bodyweight",
        "prone t raise": "bodyweight",
        "cuban press": "dumbbell",
        "dumbbell squeeze press": "dumbbell",
        "cable concentration curl": "cable",
        "suitcase deadlift": "dumbbell",
        "suitcase carry": "dumbbell",
    }

    if name_l in specific_equipment:
        return specific_equipment[name_l]

    # Generic keyword-based inference
    # Check "other" first (before "band" check, since "Foam Roll IT Band" contains "band")
    if any(x in name_l for x in ["foam roll", "sled", "prowler", "battle rope", "sandbag", "sledgehammer", "tire", "yoke", "rope climb", "medicine ball", "wall ball", "plate ", "landmine", "wrist roller", "trap bar", "fat grip", "towel", "neck harness"]):
        return "other"
    if "barbell" in name_l or "ez-bar" in name_l or "ez bar" in name_l:
        return "barbell"
    if "dumbbell" in name_l or name_l.startswith("db "):
        return "dumbbell"
    if "cable" in name_l:
        return "cable"
    if "machine" in name_l or "smith machine" in name_l or "assisted" in name_l.split() or "pec deck" in name_l or "hack squat" in name_l or "leg press" in name_l or "leg curl" in name_l or "leg extension" in name_l:
        return "machine"
    if "kettlebell" in name_l:
        return "kettlebell"
    if "band" in name_l or "banded" in name_l:
        return "band"

    # Section-based fallback (subsection_context is the ### heading, e.g. "Dumbbell", "Cable", etc.)
    ctx = section_context.lower().strip()
    if ctx == "cable":
        return "cable"
    if ctx == "barbell":
        return "barbell"
    if ctx == "dumbbell":
        return "dumbbell"
    if ctx == "machine":
        return "machine"
    if ctx == "bodyweight":
        return "bodyweight"
    if ctx == "kettlebell":
        return "kettlebell"

    return "bodyweight"

def infer_movement_pattern(name):
    name_l = name.lower()

    # Specific overrides (must come before generic checks)
    if "prowler" in name_l:
        return "other"

    # Squat patterns
    if any(x in name_l for x in ["squat", "lunge", "split squat", "step-up", "step up", "pistol", "cossack", "wall sit"]):
        return "squat"
    # Hinge patterns
    if any(x in name_l for x in ["deadlift", "rdl", "romanian", "good morning", "hip thrust", "glute bridge", "hyperextension", "hip extension", "back extension", "hip hinge", "swing", "pull-through", "pull through", "kettlebell snatch", "kettlebell clean", "clean", "snatch"]):
        return "hinge"
    # Pull patterns
    if any(x in name_l for x in ["row", "pulldown", "pull-up", "pull up", "pull-apart", "chin-up", "chin up", "curl", "face pull", "pullover", "shrug", "reverse", "lat pull", "muscle-up", "muscle up", "inverted row", "drag curl", "21s", "rope climb"]):
        return "pull"
    # Push patterns
    if any(x in name_l for x in ["press", "push-up", "push up", "pushdown", "push down", "dip", "raise", "fly", "flye", "crossover", "skull crush", "kickback", "extension", "pike", "jerk"]):
        return "push"
    # Carry patterns
    if any(x in name_l for x in ["carry", "walk", "farmer"]):
        return "carry"
    # Other
    if any(x in name_l for x in ["foam roll", "stretch", "cat-cow", "90/90", "plank", "dead bug", "bird dog", "bear crawl", "hollow", "body saw", "stir the pot", "dragon flag", "l-sit", "windshield wiper", "crunch", "sit-up", "sit up", "v-up", "leg raise", "toes-to-bar", "russian twist", "wood chop", "woodchop", "pallof", "ab roll", "ab wheel", "flutter", "scissor", "rotation", "side bend", "neck"]):
        return "other"
    if any(x in name_l for x in ["jump", "bound", "hop", "plyo", "box jump", "slam", "throw", "pass", "sprint", "burpee", "mountain climber"]):
        return "other"
    if any(x in name_l for x in ["rowing machine", "assault bike", "ski erg", "stair climber", "jump rope", "sled"]):
        return "other"
    return "other"

def infer_force_type(name, movement_pattern):
    name_l = name.lower()
    # Static holds
    if any(x in name_l for x in ["plank", "hold", "wall sit", "dead bug", "hollow hold", "l-sit", "bird dog", "copenhagen", "foam roll", "stretch", "cat-cow", "90/90", "pinch hold"]):
        return "static"
    # Carries
    if any(x in name_l for x in ["carry", "walk", "farmer", "yoke walk"]):
        return "static"
    # Specific overrides
    if "prowler push" in name_l:
        return "push"
    # Pull exercises
    if any(x in name_l for x in ["row", "pull", "curl", "chin", "shrug", "face pull", "deadlift", "clean", "snatch", "hinge", "good morning", "hip thrust", "glute bridge", "hyperextension", "back extension", "hip extension", "swing", "reverse", "drag", "21s", "rope climb", "leg raise", "toes-to-bar", "knee raise", "crunch", "sit-up", "sit up", "v-up", "ab roll", "ab wheel", "wood chop", "woodchop", "rotation", "russian twist", "flutter", "scissor", "side bend", "mountain climber", "body saw", "stir the pot", "dragon flag", "windshield wiper", "hanging", "captain", "sled pull", "sled drag"]):
        return "pull"
    if movement_pattern == "pull":
        return "pull"
    if movement_pattern == "hinge":
        return "pull"
    return "push"

def infer_body_region(name, section_context=""):
    name_l = name.lower()

    # Specific overrides (must come before generic keyword checks)
    if "sled leg press" in name_l:
        return "lower"

    # Full body
    if any(x in name_l for x in ["deadlift", "clean", "snatch", "thruster", "turkish", "burpee", "man maker", "devil press", "battle rope", "sled", "tire flip", "yoke", "prowler", "sledgehammer", "mountain climber", "bear crawl", "rope climb"]):
        return "full"
    # Lower body
    if any(x in name_l for x in ["squat", "lunge", "leg press", "leg extension", "leg curl", "calf", "tibialis", "hip thrust", "glute bridge", "hip abduct", "hip adduct", "step-up", "step up", "pistol", "cossack", "wall sit", "nordic", "glute ham", "hyperextension", "back extension", "hip extension", "reverse hyper", "fire hydrant", "frog pump", "copenhagen", "adduct", "cyclist", "spanish", "belt squat", "v-squat", "sissy", "hack squat", "jump rope calf", "sliding leg", "reverse nordic", "banded lateral walk", "lateral bound", "skater", "box jump", "broad jump", "depth jump", "jump lunge", "tuck jump", "single-leg box", "hurdle", "jump squat", "foam roll quad", "foam roll it", "foam roll ham", "foam roll calve", "foam roll glute", "hip 90/90", "hatfield", "atg split", "poliquin", "45-degree hip", "banded hip"]):
        return "lower"
    # Upper body
    if any(x in name_l for x in ["bench press", "press", "push-up", "push up", "fly", "flye", "crossover", "pec deck", "dip", "row", "pulldown", "pull-up", "pull up", "chin-up", "chin up", "curl", "extension", "pushdown", "push down", "kickback", "raise", "shrug", "face pull", "pullover", "skull crush", "reverse curl", "wrist", "farmer", "plate pinch", "towel pull", "fat grip", "finger curl", "roller", "pronation", "supination", "neck", "external rotation", "internal rotation", "band pull-apart", "bus driver", "cuban", "prone", "inverted row", "muscle-up", "scapular", "landmine", "cable shrug", "straight-arm", "foam roll lat", "foam roll thoracic", "banded face pull", "banded push", "banded row", "viking", "behind-the-neck", "bradford", "z press", "french press", "tate press", "jm press", "21s", "spider", "concentration", "bayesian", "preacher", "dragon flag", "l-sit"]):
        return "upper"

    # Section-based inference
    ctx = section_context.lower()
    if any(x in ctx for x in ["chest", "back", "shoulder", "bicep", "tricep", "forearm", "neck"]):
        return "upper"
    if any(x in ctx for x in ["quad", "hamstring", "glute", "adduct", "calf", "calve"]):
        return "lower"
    if any(x in ctx for x in ["full body", "olympic", "kettlebell", "plyometric", "cardio"]):
        return "full"
    if any(x in ctx for x in ["abs", "core"]):
        return "upper"  # core exercises classified as upper typically

    return "upper"

def infer_laterality(name):
    name_l = name.lower()
    if any(x in name_l for x in ["single-arm", "single-leg", "single arm", "single leg", "one-arm", "one-leg", "unilateral", "concentration", "pistol", "meadows", "kroc", "suitcase"]):
        return "unilateral"
    # Bulgarian split squat, split squat, lunges are unilateral
    if any(x in name_l for x in ["split squat", "lunge", "step-up", "step up", "lateral bound", "skater"]):
        return "unilateral"
    return "bilateral"

def infer_is_compound(name):
    name_l = name.lower()
    # Isolation exercises
    if any(x in name_l for x in ["curl", "extension", "raise", "fly", "flye", "kickback", "pushdown", "push down", "crossover", "pec deck", "reverse pec", "shrug", "wrist", "calf raise", "tibialis", "rotation", "crunch", "leg raise", "side bend", "pronation", "supination", "finger curl", "neck curl", "neck extension", "neck lateral", "halo", "bus driver", "21s"]):
        # But some "extensions" are compound
        if any(x in name_l for x in ["back extension", "hyperextension", "hip extension", "reverse hyper", "bodyweight tricep extension"]):
            return True
        return False
    # Isolation-like
    if any(x in name_l for x in ["plank", "side plank", "dead bug", "hollow hold", "bird dog", "fire hydrant", "frog pump", "wall sit", "foam roll", "stretch", "cat-cow", "90/90"]):
        return False
    return True

def get_section_for_exercise(num, md_text):
    """Find which section heading an exercise number falls under."""
    lines = md_text.split('\n')
    current_section = ""
    for line in lines:
        if line.startswith('## '):
            current_section = line.strip('# ').strip()
        m = re.match(r'^\s*' + str(num) + r'\.', line)
        if m:
            return current_section
    return ""

def generate_aliases(name):
    """Generate common aliases for an exercise."""
    aliases = []
    name_l = name.lower()

    alias_map = {
        "Floor Press": ["Barbell Floor Press"],
        "Larsen Press": [],
        "Dumbbell Floor Press": ["DB Floor Press"],
        "Squeeze Press": ["Dumbbell Squeeze Press"],
        "Machine Incline Press": ["Incline Machine Press"],
        "Smith Machine Incline Press": ["Smith Incline Press"],
        "Decline Push-Up": ["Decline Pushup"],
        "Incline Push-Up": ["Incline Pushup"],
        "Wide Push-Up": ["Wide Pushup"],
        "Pike Push-Up": ["Pike Pushup"],
        "Chest-Supported Dumbbell Row": ["Chest Supported Row", "Incline DB Row"],
        "Kroc Row": ["Kroc Dumbbell Row"],
        "Gorilla Row": [],
        "Renegade Row": [],
        "Seal Row": [],
        "Straight-Arm Pulldown": ["Straight Arm Lat Pulldown"],
        "Single-Arm Lat Pulldown": ["One-Arm Lat Pulldown"],
        "Wide-Grip Lat Pulldown": ["Wide Grip Pulldown"],
        "Reverse-Grip Lat Pulldown": ["Reverse Grip Pulldown", "Underhand Pulldown"],
        "Single-Arm Cable Row": ["One-Arm Cable Row"],
        "Chest-Supported Machine Row": ["Chest Supported Row Machine"],
        "Assisted Pull-Up Machine": ["Assisted Pull-Up"],
        "Inverted Row": ["Body Row", "Australian Pull-Up"],
        "Neutral-Grip Pull-Up": ["Hammer Grip Pull-Up"],
        "Muscle-Up": ["Bar Muscle-Up"],
        "Scapular Pull-Up": ["Scap Pull-Up"],
        "Landmine Row": ["T-Bar Landmine Row"],
        "Cable Shrug": [],
        "Push Press": ["Barbell Push Press"],
        "Behind-the-Neck Press": ["BTN Press"],
        "Bradford Press": [],
        "Z Press": ["Seated Floor Press"],
        "Dumbbell Y Raise": ["Y Raise"],
        "Dumbbell Lu Raise": ["Lu Raise"],
        "Dumbbell W Raise": ["W Raise"],
        "Cable Front Raise": [],
        "Cable Rear Delt Fly": ["Cable Reverse Fly"],
        "Cable Upright Row": [],
        "Machine Rear Delt Fly": ["Reverse Machine Fly"],
        "Handstand Push-Up": ["Handstand Pushup", "HSPU"],
        "Landmine Lateral Raise": [],
        "Plate Front Raise": [],
        "Band Pull-Apart": ["Banded Pull-Apart"],
        "Bus Driver": ["Plate Bus Driver"],
        "Dumbbell External Rotation": ["DB External Rotation"],
        "Cable External Rotation": [],
        "Cable Internal Rotation": [],
        "Band External Rotation": ["Banded External Rotation"],
        "Prone Y Raise": [],
        "Prone T Raise": [],
        "Cuban Press": ["Cuban Rotation"],
        "Drag Curl": ["Barbell Drag Curl"],
        "Wide-Grip Barbell Curl": ["Wide Grip Curl"],
        "Zottman Curl": [],
        "Cross-Body Hammer Curl": ["Cross Body Curl"],
        "Prone Incline Curl": ["Incline Prone Curl"],
        "Cable Hammer Curl": ["Rope Cable Curl"],
        "Overhead Cable Curl": ["High Cable Curl"],
        "Single-Arm Cable Curl": ["One-Arm Cable Curl"],
        "Machine Bicep Curl": [],
        "Chin-Up Curl": ["Supinated Chin-Up"],
        "Body Drag Curl": ["Bodyweight Drag Curl"],
        "JM Press": ["JM Bench Press"],
        "Floor Skull Crusher": ["Floor Tricep Extension"],
        "Tate Press": [],
        "Single-Arm Dumbbell Overhead Extension": ["One-Arm DB Overhead Extension"],
        "Tricep Pushdown (Rope)": ["Rope Pushdown"],
        "Tricep Pushdown (Reverse Grip)": ["Reverse Grip Pushdown"],
        "Cable Kickback": ["Cable Tricep Kickback"],
        "Machine Tricep Extension": [],
        "Assisted Dip Machine": ["Assisted Dip"],
        "Bench Dip": [],
        "Bodyweight Tricep Extension": ["Bodyweight Skull Crusher"],
        "Band Pushdown": ["Banded Tricep Pushdown"],
        "Behind-the-Back Wrist Curl": [],
        "Plate Pinch Hold": ["Plate Pinch"],
        "Towel Pull-Up": [],
        "Fat Grip Barbell Hold": ["Fat Grip Hold"],
        "Wrist Roller": [],
        "Pronation/Supination": ["Forearm Rotation"],
        "Finger Curl": [],
        "Overhead Squat": ["OHS"],
        "Dumbbell Squat": ["DB Squat"],
        "Dumbbell Bulgarian Split Squat": ["DB Bulgarian Split Squat"],
        "Belt Squat": [],
        "V-Squat Machine": ["V-Squat"],
        "Single-Leg Leg Press": ["One-Leg Leg Press"],
        "Pistol Squat": ["Single-Leg Squat"],
        "Bodyweight Squat": ["Air Squat"],
        "Jump Squat": ["Squat Jump"],
        "Wall Sit": ["Wall Squat"],
        "Cyclist Squat": ["Heel-Elevated Squat"],
        "Split Squat": ["Static Lunge"],
        "Cossack Squat": ["Cossack Lunge"],
        "Landmine Squat": [],
        "Spanish Squat": ["Banded Spanish Squat"],
        "Stiff-Leg Deadlift": ["Stiff-Legged Deadlift", "SLDL"],
        "Dumbbell Romanian Deadlift": ["DB RDL"],
        "Cable Romanian Deadlift": ["Cable RDL"],
        "Single-Leg Leg Curl": ["One-Leg Leg Curl"],
        "Sliding Leg Curl": ["Slider Hamstring Curl"],
        "Reverse Nordic Curl": [],
        "Banded Good Morning": [],
        "Hip Hinge (Band)": ["Banded Hip Hinge"],
        "45-Degree Back Extension": ["45-Degree Hyper"],
        "Reverse Lunge": ["Barbell Reverse Lunge"],
        "Deficit Lunge": [],
        "Curtsy Lunge": ["Crossover Lunge"],
        "Smith Machine Hip Thrust": [],
        "Dumbbell Lunge": ["DB Lunge"],
        "Dumbbell Step-Up": ["DB Step-Up"],
        "Dumbbell Hip Thrust": ["DB Hip Thrust"],
        "Single-Leg Hip Thrust": ["One-Leg Hip Thrust"],
        "Cable Hip Extension": ["Cable Glute Kickback"],
        "Reverse Hyperextension": ["Reverse Hyper"],
        "Glute Bridge": ["Bodyweight Glute Bridge"],
        "Frog Pump": [],
        "Fire Hydrant": [],
        "Cable Hip Adduction": [],
        "Copenhagen Plank": ["Copenhagen Adductor Plank"],
        "Band Hip Adduction": ["Banded Hip Adduction"],
        "Smith Machine Calf Raise": [],
        "Single-Leg Calf Raise": ["One-Leg Calf Raise"],
        "Tibialis Raise": ["Tib Raise"],
        "Barbell Calf Raise": [],
        "Dumbbell Calf Raise": ["DB Calf Raise"],
        "Jump Rope Calf Bounce": [],
        "Calf Raise (Bodyweight)": ["Bodyweight Calf Raise"],
        "Sit-Up": [],
        "V-Up": ["V Up"],
        "Weighted Crunch": [],
        "Machine Crunch": ["Ab Crunch Machine"],
        "GHD Sit-Up": ["GHD Situp"],
        "Lying Leg Raise": ["Supine Leg Raise"],
        "Hanging Knee Raise": [],
        "Reverse Crunch": [],
        "Flutter Kick": ["Flutter Kicks"],
        "Scissor Kick": ["Scissor Kicks"],
        "Captain's Chair Leg Raise": ["Captain's Chair"],
        "Oblique Crunch": [],
        "Landmine Rotation": ["Landmine Twist"],
        "Cable Woodchop (High to Low)": ["High-to-Low Woodchop"],
        "Cable Woodchop (Low to High)": ["Low-to-High Woodchop"],
        "Dumbbell Side Bend": ["Side Bend"],
        "Windshield Wiper": ["Windshield Wipers"],
        "Hollow Hold": [],
        "Body Saw": [],
        "Stir the Pot": [],
        "Weighted Plank": [],
        "Bird Dog": [],
        "Bear Crawl": [],
        "Neck Curl": ["Neck Flexion"],
        "Neck Extension": [],
        "Neck Lateral Flexion": ["Neck Side Raise"],
        "Neck Harness Extension": ["Neck Harness"],
        "Jefferson Deadlift": [],
        "Suitcase Deadlift": [],
        "Snatch": ["Barbell Snatch"],
        "Clean": ["Barbell Clean"],
        "Hang Clean": ["Barbell Hang Clean"],
        "Hang Snatch": ["Barbell Hang Snatch"],
        "Clean and Jerk": ["Barbell Clean and Jerk", "C&J"],
        "Push Jerk": ["Barbell Push Jerk"],
        "Muscle Snatch": [],
        "Dumbbell Snatch": ["DB Snatch"],
        "Dumbbell Clean and Press": ["DB Clean and Press"],
        "Kettlebell Snatch": ["KB Snatch"],
        "Kettlebell Clean": ["KB Clean"],
        "Sled Pull": [],
        "Tire Flip": [],
        "Yoke Walk": ["Yoke Carry"],
        "Trap Bar Carry": ["Trap Bar Walk"],
        "Kettlebell Goblet Squat": ["KB Goblet Squat"],
        "Kettlebell Press": ["KB Press"],
        "Kettlebell Row": ["KB Row"],
        "Kettlebell Deadlift": ["KB Deadlift"],
        "Kettlebell Thruster": ["KB Thruster"],
        "Kettlebell High Pull": ["KB High Pull"],
        "Kettlebell Windmill": ["KB Windmill"],
        "Kettlebell Halo": ["KB Halo"],
        "Double Kettlebell Swing": ["Double KB Swing"],
        "Kettlebell Sumo Squat": ["KB Sumo Squat"],
        "Broad Jump": ["Standing Long Jump"],
        "Depth Jump": [],
        "Jump Lunge": ["Jumping Lunge", "Plyometric Lunge"],
        "Lateral Bound": [],
        "Skater Jump": ["Skater"],
        "Tuck Jump": [],
        "Single-Leg Box Jump": ["One-Leg Box Jump"],
        "Hurdle Hop": [],
        "Plyo Push-Up": ["Plyometric Push-Up", "Clap Push-Up"],
        "Medicine Ball Slam": ["Med Ball Slam"],
        "Medicine Ball Chest Pass": ["Med Ball Chest Pass"],
        "Medicine Ball Rotational Throw": ["Med Ball Rotational Throw"],
        "Wall Ball": ["Wall Ball Shot"],
        "Box Jump (Step Down)": ["Step-Down Box Jump"],
        "Rowing Machine": ["Erg", "Rower"],
        "Assault Bike": ["Air Bike", "Fan Bike"],
        "Ski Erg": ["SkiErg"],
        "Stair Climber": ["Stair Master", "StairMaster"],
        "Jump Rope": ["Skipping"],
        "Burpee": [],
        "Mountain Climber": ["Mountain Climbers"],
        "Sprint": ["Sprints"],
        "Sled Drag": ["Sled Backward Drag"],
        "Foam Roll Quads": [],
        "Foam Roll IT Band": [],
        "Foam Roll Lats": [],
        "Foam Roll Thoracic Spine": ["Foam Roll T-Spine"],
        "Foam Roll Hamstrings": [],
        "Foam Roll Calves": [],
        "Foam Roll Glutes": [],
        "Hip 90/90 Stretch": ["90/90 Stretch"],
        "World's Greatest Stretch": ["WGS"],
        "Cat-Cow": ["Cat Cow"],
        "Banded Face Pull": ["Band Face Pull"],
        "Banded Lateral Walk": ["Band Lateral Walk", "Monster Walk"],
        "Banded Squat": ["Band Squat"],
        "Banded Deadlift": ["Band Deadlift"],
        "Banded Push-Up": ["Band Push-Up"],
        "Banded Row": ["Band Row"],
        "Dumbbell Squeeze Press": ["Squeeze Press"],
        "Behind-the-Neck Lat Pulldown": ["BTN Pulldown"],
        "Prone Row": [],
        "Viking Press": ["Landmine Viking Press"],
        "Smith Machine Shoulder Press": ["Smith Shoulder Press"],
        "Lateral Raise (Cable, Behind Back)": ["Behind-Back Cable Lateral Raise"],
        "21s (Barbell Curl)": ["21s", "7-7-7 Curl"],
        "EZ-Bar Preacher Curl": [],
        "Cable Concentration Curl": [],
        "French Press (EZ-Bar)": ["EZ-Bar French Press", "EZ-Bar Overhead Extension"],
        "Jefferson Squat": [],
        "Hatfield Squat": [],
        "ATG Split Squat": ["ATG Lunge"],
        "Poliquin Step-Up": ["Peterson Step-Up"],
        "Sled Leg Press (Vertical)": ["Vertical Leg Press"],
        "45-Degree Hip Extension": ["45-Degree Hip Extension Machine"],
        "Banded Hip Thrust": ["Band Hip Thrust"],
        "Smith Machine Lunge": [],
        "Dragon Flag": [],
        "L-Sit": ["L Sit"],
        "Suitcase Carry": [],
        "Ab Wheel (Kneeling)": ["Kneeling Ab Wheel", "Ab Wheel Rollout"],
        "Hanging Windshield Wiper": [],
        "Man Maker": ["Manmaker"],
        "Devil Press": [],
        "Sandbag Clean": [],
        "Rope Climb": [],
        "Prowler Push": ["Prowler"],
        "Sledgehammer Swing": ["Sledgehammer Tire Hit"],
    }

    return alias_map.get(name, [])

def generate_instructions(name, section_context=""):
    """Generate concise instructions for exercises not found in free-exercise-db."""
    instructions_map = {
        "Floor Press": [
            "Lie on the floor with knees bent and feet flat",
            "Grip the barbell at shoulder width and unrack",
            "Lower the bar until upper arms touch the floor",
            "Pause briefly, then press up to lockout"
        ],
        "Larsen Press": [
            "Lie on a flat bench with legs extended straight and feet off the floor",
            "Grip the barbell slightly wider than shoulder-width",
            "Lower the bar to mid-chest with control",
            "Press up to full extension while maintaining leg position"
        ],
        "Dumbbell Floor Press": [
            "Lie on the floor holding dumbbells at chest level",
            "Press dumbbells up until arms are fully extended",
            "Lower until upper arms rest on the floor",
            "Pause briefly, then press back up"
        ],
        "Squeeze Press": [
            "Lie on a flat bench pressing two dumbbells together",
            "Keep the dumbbells squeezed together throughout the movement",
            "Press up to full extension maintaining inward pressure",
            "Lower to chest while keeping dumbbells in contact"
        ],
        "Machine Incline Press": [
            "Adjust the seat so handles are at upper chest level",
            "Press the handles forward and up to full extension",
            "Lower with control back to the starting position"
        ],
        "Smith Machine Incline Press": [
            "Set bench to 30-45 degrees inside the Smith machine",
            "Grip the bar slightly wider than shoulder-width",
            "Unrack and lower the bar to upper chest",
            "Press up to full extension"
        ],
        "Decline Push-Up": [
            "Place feet on an elevated surface with hands on the floor",
            "Set hands slightly wider than shoulder-width",
            "Lower chest toward the floor",
            "Push back up to full arm extension"
        ],
        "Incline Push-Up": [
            "Place hands on an elevated surface like a bench or box",
            "Set hands slightly wider than shoulder-width",
            "Lower chest toward the surface",
            "Push back up to full arm extension"
        ],
        "Wide Push-Up": [
            "Start in push-up position with hands wider than shoulder-width",
            "Lower chest toward the floor keeping elbows flared",
            "Push back up to full arm extension"
        ],
        "Pike Push-Up": [
            "Start in a downward dog position with hips high",
            "Bend elbows to lower the top of your head toward the floor",
            "Press back up to the starting position",
            "Keep hips elevated throughout"
        ],
        "Chest-Supported Dumbbell Row": [
            "Set an incline bench to 30-45 degrees",
            "Lie face down on the bench holding dumbbells",
            "Row both dumbbells up toward your hips, squeezing shoulder blades",
            "Lower with control to full arm extension"
        ],
        "Kroc Row": [
            "Place one hand on a bench for support with feet staggered",
            "Hold a heavy dumbbell in the other hand at arm's length",
            "Row the dumbbell to your hip using momentum on the last few reps",
            "Focus on high reps with heavy weight and controlled eccentric"
        ],
        "Gorilla Row": [
            "Stand over two kettlebells or dumbbells in a hip-hinge position",
            "Row one weight up while pressing the other into the floor",
            "Alternate sides with each rep",
            "Keep your back flat and core braced"
        ],
        "Renegade Row": [
            "Start in a push-up position gripping two dumbbells",
            "Row one dumbbell to your hip while stabilizing on the other",
            "Lower the weight and repeat on the other side",
            "Keep hips square to the floor throughout"
        ],
        "Seal Row": [
            "Lie face down on an elevated bench with arms hanging straight down",
            "Hold a barbell or dumbbells at arm's length",
            "Row the weight up toward the bench, squeezing shoulder blades",
            "Lower with control to full extension"
        ],
        "Straight-Arm Pulldown": [
            "Stand facing a cable machine with a bar attachment at the top",
            "With arms straight, pull the bar down in an arc to your thighs",
            "Squeeze your lats at the bottom",
            "Return slowly to the starting position"
        ],
        "Single-Arm Lat Pulldown": [
            "Sit at a lat pulldown machine with a single handle attachment",
            "Pull the handle down to your side, focusing on one lat",
            "Squeeze at the bottom and control the return"
        ],
        "Wide-Grip Lat Pulldown": [
            "Grip the bar wider than shoulder-width at a lat pulldown station",
            "Pull the bar down to your upper chest",
            "Squeeze your lats at the bottom",
            "Return with control to full arm extension"
        ],
        "Reverse-Grip Lat Pulldown": [
            "Grip the lat pulldown bar with an underhand grip at shoulder-width",
            "Pull the bar down to your upper chest",
            "Focus on squeezing the lower lats",
            "Return with control to full extension"
        ],
        "Single-Arm Cable Row": [
            "Set a cable to mid-height with a single handle",
            "Stand or kneel and pull the handle toward your hip",
            "Squeeze your shoulder blade at full contraction",
            "Return slowly to the starting position"
        ],
        "Chest-Supported Machine Row": [
            "Sit with chest against the pad on the machine row",
            "Grip the handles and pull toward your torso",
            "Squeeze your shoulder blades together at full contraction",
            "Return with control"
        ],
        "Assisted Pull-Up Machine": [
            "Set the counterweight to desired assistance level",
            "Kneel or stand on the platform and grip the handles",
            "Pull yourself up until chin is above the bar",
            "Lower with control to full arm extension"
        ],
        "Inverted Row": [
            "Set a barbell in a rack at waist height",
            "Hang underneath with arms extended and body straight",
            "Pull your chest to the bar by squeezing shoulder blades",
            "Lower with control back to full extension"
        ],
        "Neutral-Grip Pull-Up": [
            "Grip parallel handles with palms facing each other",
            "Pull yourself up until chin clears the handles",
            "Lower with control to full arm extension"
        ],
        "Muscle-Up": [
            "Hang from a pull-up bar with a false grip",
            "Pull explosively, transitioning from below to above the bar",
            "Press up to full arm extension on top of the bar",
            "Lower back down with control"
        ],
        "Scapular Pull-Up": [
            "Hang from a pull-up bar with arms fully extended",
            "Without bending your elbows, retract and depress your shoulder blades",
            "Hold the top position briefly",
            "Relax back to a dead hang and repeat"
        ],
        "Landmine Row": [
            "Straddle the end of a loaded landmine barbell",
            "Hinge at the hips and grip the bar with both hands or a V-handle",
            "Row the bar toward your chest",
            "Lower with control"
        ],
        "Cable Shrug": [
            "Stand between two low cable pulleys holding the handles",
            "Shrug your shoulders straight up toward your ears",
            "Hold the top position briefly",
            "Lower with control"
        ],
        "Push Press": [
            "Hold a barbell at shoulder height in the front rack position",
            "Dip your knees slightly and drive the bar overhead using leg drive",
            "Lock out arms at the top",
            "Lower the bar back to shoulders with control"
        ],
        "Behind-the-Neck Press": [
            "Sit or stand with a barbell resting behind your neck on your traps",
            "Press the bar overhead to full lockout",
            "Lower the bar back behind your neck with control",
            "Use lighter weight and ensure adequate shoulder mobility"
        ],
        "Bradford Press": [
            "Start with a barbell at the front rack position at shoulder height",
            "Press the bar just high enough to clear your head",
            "Lower behind your neck, then immediately press back over to the front",
            "Alternate front-to-back without locking out"
        ],
        "Z Press": [
            "Sit on the floor with legs extended straight in front",
            "Clean or rack a barbell to shoulder height",
            "Press the bar overhead to full lockout without leaning back",
            "Lower with control back to shoulders"
        ],
        "Dumbbell Y Raise": [
            "Stand or lie face down on an incline bench holding light dumbbells",
            "Raise the dumbbells up and out at a 45-degree angle forming a Y shape",
            "Lower with control back to the starting position"
        ],
        "Dumbbell Lu Raise": [
            "Stand holding a dumbbell in each hand at your sides",
            "Perform a lateral raise to shoulder height",
            "At the top, rotate and press the dumbbells overhead",
            "Reverse the motion back to starting position"
        ],
        "Dumbbell W Raise": [
            "Lie face down on an incline bench holding light dumbbells",
            "Raise the dumbbells with elbows bent to form a W shape",
            "Squeeze shoulder blades together at the top",
            "Lower with control"
        ],
        "Cable Front Raise": [
            "Stand facing away from a low cable with a handle or rope",
            "With arm straight, raise the handle forward to shoulder height",
            "Lower with control back to your side"
        ],
        "Cable Rear Delt Fly": [
            "Set cables to shoulder height with crossover handles",
            "Pull the handles outward and back, squeezing rear delts",
            "Control the return to the starting position"
        ],
        "Cable Upright Row": [
            "Stand facing a low cable pulley with a straight bar attachment",
            "Pull the bar up along your body toward chin height",
            "Keep elbows high and lead with your elbows",
            "Lower with control"
        ],
        "Machine Rear Delt Fly": [
            "Sit facing the pad on a pec deck or rear delt machine",
            "Grip the handles and push them back in a reverse fly motion",
            "Squeeze your rear delts at full contraction",
            "Return with control"
        ],
        "Handstand Push-Up": [
            "Kick up into a handstand against a wall",
            "Lower yourself by bending your elbows until your head lightly touches the floor",
            "Press back up to full arm extension",
            "Maintain a tight core throughout"
        ],
        "Landmine Lateral Raise": [
            "Stand with one end of a landmine barbell at your side",
            "Grip the end of the bar with the working hand",
            "Raise the bar out to the side to shoulder height",
            "Lower with control"
        ],
        "Plate Front Raise": [
            "Stand holding a weight plate with both hands at waist level",
            "Raise the plate forward and up to shoulder height with arms straight",
            "Lower with control"
        ],
        "Band Pull-Apart": [
            "Hold a resistance band in front of you at shoulder height with arms extended",
            "Pull the band apart by squeezing your shoulder blades together",
            "Return to the starting position with control"
        ],
        "Bus Driver": [
            "Stand holding a weight plate with both hands at arm's length in front",
            "Rotate the plate like a steering wheel, alternating sides",
            "Keep arms extended and core braced throughout"
        ],
        "Dumbbell External Rotation": [
            "Lie on your side with a light dumbbell in the top hand",
            "Keep your upper arm pinned to your side with elbow bent at 90 degrees",
            "Rotate your forearm upward away from your body",
            "Lower with control back to the starting position"
        ],
        "Cable External Rotation": [
            "Stand sideways to a cable set at elbow height",
            "Keep your elbow pinned to your side bent at 90 degrees",
            "Rotate your forearm outward away from the cable",
            "Return with control"
        ],
        "Cable Internal Rotation": [
            "Stand sideways to a cable set at elbow height",
            "Keep your elbow pinned to your side bent at 90 degrees",
            "Rotate your forearm inward toward your body",
            "Return with control"
        ],
        "Band External Rotation": [
            "Attach a band at elbow height and stand sideways",
            "Keep your elbow pinned to your side bent at 90 degrees",
            "Rotate your forearm outward against the band's resistance",
            "Return with control"
        ],
        "Prone Y Raise": [
            "Lie face down on a flat bench or the floor with arms hanging down",
            "Raise both arms up and outward to form a Y shape with thumbs up",
            "Squeeze your lower traps at the top",
            "Lower with control"
        ],
        "Prone T Raise": [
            "Lie face down on a flat bench or the floor with arms hanging down",
            "Raise both arms straight out to the sides to form a T shape",
            "Squeeze your mid-back at the top",
            "Lower with control"
        ],
        "Cuban Press": [
            "Stand holding dumbbells with an overhand grip",
            "Perform an upright row to shoulder height",
            "Externally rotate the dumbbells until forearms point up",
            "Press overhead, then reverse the entire sequence"
        ],
        "Drag Curl": [
            "Stand holding a barbell with an underhand grip",
            "Curl the bar up while dragging it along your torso",
            "Keep your elbows behind the bar throughout",
            "Lower with control along the same path"
        ],
        "Wide-Grip Barbell Curl": [
            "Stand holding a barbell with a wider-than-shoulder underhand grip",
            "Curl the bar up toward your shoulders",
            "Squeeze at the top and lower with control"
        ],
        "Zottman Curl": [
            "Stand holding dumbbells with palms facing up",
            "Curl the dumbbells up with a supinated grip",
            "At the top, rotate to a pronated (palms-down) grip",
            "Lower slowly with the pronated grip, then rotate back at the bottom"
        ],
        "Cross-Body Hammer Curl": [
            "Stand holding a dumbbell in each hand at your sides",
            "Curl one dumbbell across your body toward the opposite shoulder",
            "Lower with control and alternate sides"
        ],
        "Prone Incline Curl": [
            "Lie face down on an incline bench with arms hanging straight down",
            "Hold dumbbells with palms forward",
            "Curl the dumbbells up while keeping upper arms stationary",
            "Lower with control"
        ],
        "Cable Hammer Curl": [
            "Attach a rope to a low cable pulley",
            "Stand facing the machine and grip the rope with neutral grip",
            "Curl the rope up keeping palms facing each other",
            "Lower with control"
        ],
        "Overhead Cable Curl": [
            "Stand between two high cable pulleys with handles attached",
            "Grip the handles with palms facing up and arms extended to the sides",
            "Curl the handles toward your head by flexing your biceps",
            "Return with control to the starting position"
        ],
        "Single-Arm Cable Curl": [
            "Stand facing a low cable with a single handle",
            "Curl the handle up toward your shoulder",
            "Squeeze at the top and lower with control"
        ],
        "Machine Bicep Curl": [
            "Sit at the bicep curl machine with arms on the pad",
            "Grip the handles and curl toward your shoulders",
            "Squeeze at the top and lower with control"
        ],
        "Chin-Up Curl": [
            "Hang from a pull-up bar with a narrow supinated grip",
            "Pull yourself up focusing on bicep contraction",
            "Lower with control to full extension"
        ],
        "Body Drag Curl": [
            "Stand upright and mimic a curl motion using body leverage",
            "Drag your hands up along your body using a bar or surface",
            "Focus on the bicep contraction throughout",
            "Lower with control"
        ],
        "JM Press": [
            "Lie on a flat bench and grip the barbell at close grip width",
            "Lower the bar toward your chin/throat area by bending at the elbows",
            "The bar path combines a skull crusher and close-grip press",
            "Press back to lockout"
        ],
        "Floor Skull Crusher": [
            "Lie on the floor holding an EZ-bar or dumbbells above your chest",
            "Lower the weight toward your forehead by bending at the elbows",
            "Let your upper arms touch the floor briefly",
            "Extend back to the starting position"
        ],
        "Tate Press": [
            "Lie on a flat bench holding dumbbells above your chest with palms facing your feet",
            "Lower the dumbbells inward toward your chest by bending at the elbows",
            "The dumbbells should touch your chest near the midline",
            "Press back up to full extension"
        ],
        "Single-Arm Dumbbell Overhead Extension": [
            "Stand or sit holding one dumbbell overhead with arm fully extended",
            "Lower the dumbbell behind your head by bending at the elbow",
            "Extend back to the starting position",
            "Keep your upper arm close to your head"
        ],
        "Tricep Pushdown (Rope)": [
            "Attach a rope to a high cable pulley",
            "Grip the rope with neutral grip and elbows at your sides",
            "Push down and spread the rope apart at the bottom",
            "Return with control to the starting position"
        ],
        "Tricep Pushdown (Reverse Grip)": [
            "Attach a straight bar to a high cable pulley",
            "Grip the bar with an underhand (supinated) grip",
            "Push down to full arm extension keeping elbows pinned",
            "Return with control"
        ],
        "Cable Kickback": [
            "Set a cable to the lowest position with a single handle",
            "Hinge forward and keep your upper arm parallel to your torso",
            "Extend your forearm back until your arm is straight",
            "Return with control"
        ],
        "Machine Tricep Extension": [
            "Sit at the tricep extension machine and grip the handles",
            "Extend your arms fully against the resistance",
            "Return with control to the starting position"
        ],
        "Assisted Dip Machine": [
            "Set the counterweight to desired assistance level",
            "Kneel or stand on the platform and grip the dip handles",
            "Lower your body by bending your elbows to 90 degrees",
            "Press back up to full extension"
        ],
        "Bench Dip": [
            "Place your hands on the edge of a bench behind you with fingers forward",
            "Extend your legs out in front",
            "Lower your body by bending your elbows to about 90 degrees",
            "Press back up to full extension"
        ],
        "Bodyweight Tricep Extension": [
            "Place your hands on a bar or surface at about waist height",
            "Lean forward with arms extended and body at an angle",
            "Lower your head under the bar by bending at the elbows",
            "Press back to the starting position"
        ],
        "Band Pushdown": [
            "Attach a resistance band to a high anchor point",
            "Grip the band with both hands at chest height",
            "Push down to full arm extension keeping elbows at your sides",
            "Return with control"
        ],
        "Behind-the-Back Wrist Curl": [
            "Stand holding a barbell behind your back with an underhand grip",
            "Curl your wrists upward, flexing the forearms",
            "Lower with control and repeat"
        ],
        "Plate Pinch Hold": [
            "Pinch two weight plates together smooth-side-out between your fingers and thumb",
            "Hold at your side with arm extended for time",
            "Focus on gripping with fingertips"
        ],
        "Towel Pull-Up": [
            "Drape a towel over a pull-up bar and grip each end",
            "Perform a pull-up while squeezing the towel tightly",
            "Lower with control to full extension"
        ],
        "Fat Grip Barbell Hold": [
            "Attach fat grips to a barbell or use a thick bar",
            "Deadlift the bar to lockout and hold for time",
            "Focus on maintaining grip"
        ],
        "Wrist Roller": [
            "Hold a wrist roller device with arms extended in front",
            "Roll the weight up by alternately flexing each wrist",
            "Reverse the motion to lower the weight",
            "Keep arms parallel to the floor throughout"
        ],
        "Pronation/Supination": [
            "Hold a light dumbbell or hammer by one end with elbow at your side",
            "Rotate your forearm inward (pronation) then outward (supination)",
            "Perform slowly with control through full range of motion"
        ],
        "Finger Curl": [
            "Hold a barbell with an overhand grip and let it roll to your fingertips",
            "Curl your fingers to bring the bar back into your palm",
            "Squeeze at the top and lower with control"
        ],
        "Overhead Squat": [
            "Hold a barbell overhead with a wide snatch grip",
            "Squat down while keeping the bar directly overhead",
            "Keep your chest up and core braced",
            "Drive back up to standing"
        ],
        "Dumbbell Squat": [
            "Stand holding dumbbells at your sides",
            "Squat down until thighs are parallel to the floor",
            "Drive through your heels to stand back up"
        ],
        "Dumbbell Bulgarian Split Squat": [
            "Hold dumbbells at your sides with one foot elevated behind you on a bench",
            "Lower your back knee toward the floor",
            "Drive through the front foot to return to standing"
        ],
        "Belt Squat": [
            "Attach a weight belt to a belt squat machine or low pulley",
            "Stand on the platform with feet shoulder-width apart",
            "Squat down until thighs are parallel",
            "Drive up to standing"
        ],
        "V-Squat Machine": [
            "Stand on the V-squat machine platform with shoulders under the pads",
            "Squat down until thighs are parallel to the floor",
            "Drive up to the starting position"
        ],
        "Single-Leg Leg Press": [
            "Sit on the leg press machine and place one foot on the platform",
            "Lower the sled by bending your knee to 90 degrees",
            "Press the sled back up to full extension",
            "Complete all reps on one side before switching"
        ],
        "Pistol Squat": [
            "Stand on one leg with the other leg extended straight in front",
            "Squat down as deep as possible while keeping the raised leg off the floor",
            "Drive back up to standing on one leg",
            "Use arms for counterbalance as needed"
        ],
        "Bodyweight Squat": [
            "Stand with feet shoulder-width apart",
            "Squat down until thighs are parallel to the floor",
            "Keep your chest up and knees tracking over toes",
            "Drive through your heels to stand back up"
        ],
        "Jump Squat": [
            "Stand with feet shoulder-width apart",
            "Squat down to parallel, then explode upward into a jump",
            "Land softly with knees slightly bent",
            "Immediately descend into the next rep"
        ],
        "Wall Sit": [
            "Stand with your back flat against a wall",
            "Slide down until your thighs are parallel to the floor",
            "Keep your back pressed against the wall and hold the position",
            "Hold for the prescribed duration"
        ],
        "Cyclist Squat": [
            "Stand with heels elevated on small plates and feet close together",
            "Squat straight down keeping your torso upright",
            "Focus on quad engagement with knees traveling forward",
            "Drive back up to standing"
        ],
        "Split Squat": [
            "Stand in a staggered stance with one foot forward",
            "Lower your back knee toward the floor",
            "Drive through the front foot to return to standing",
            "Keep your torso upright throughout"
        ],
        "Cossack Squat": [
            "Stand with a wide stance, toes pointed slightly outward",
            "Shift your weight to one leg and squat down on that side",
            "Keep the opposite leg straight with foot flat on the floor",
            "Return to center and alternate sides"
        ],
        "Landmine Squat": [
            "Hold the end of a landmine barbell at chest height",
            "Squat down until thighs are parallel",
            "Drive up to standing",
            "Keep the bar close to your chest throughout"
        ],
        "Spanish Squat": [
            "Loop a band behind your knees and anchor it to a fixed point",
            "Lean back into the band and squat down",
            "Keep your shins vertical and focus on quad engagement",
            "Drive back up to standing"
        ],
        "Stiff-Leg Deadlift": [
            "Stand holding a barbell with an overhand grip",
            "Hinge at the hips with legs nearly straight (slight knee bend)",
            "Lower the bar along your legs until you feel a hamstring stretch",
            "Drive hips forward to return to standing"
        ],
        "Dumbbell Romanian Deadlift": [
            "Stand holding dumbbells in front of your thighs",
            "Hinge at the hips, pushing them back while keeping a slight knee bend",
            "Lower the dumbbells along your legs until you feel a hamstring stretch",
            "Drive hips forward to return to standing"
        ],
        "Cable Romanian Deadlift": [
            "Stand facing a low cable pulley with a bar attachment",
            "Hinge at the hips, pushing them back while keeping a slight knee bend",
            "Lower until you feel a hamstring stretch",
            "Drive hips forward to return to standing"
        ],
        "Single-Leg Leg Curl": [
            "Lie face down on a leg curl machine with one leg under the pad",
            "Curl your heel toward your glute",
            "Lower with control and complete all reps before switching"
        ],
        "Sliding Leg Curl": [
            "Lie on your back with heels on sliders or a towel on a smooth floor",
            "Bridge your hips up and slide your feet away from you",
            "Curl your feet back toward your glutes while maintaining the bridge",
            "Maintain hip extension throughout"
        ],
        "Reverse Nordic Curl": [
            "Kneel on a pad with your torso upright",
            "Slowly lean back by extending at the knees, keeping hips extended",
            "Go as far back as you can control",
            "Use your quads to pull yourself back upright"
        ],
        "Banded Good Morning": [
            "Loop a band under your feet and over the back of your neck",
            "Hinge at the hips with a slight knee bend",
            "Push your hips back until you feel a hamstring stretch",
            "Drive hips forward to return to standing"
        ],
        "Hip Hinge (Band)": [
            "Loop a band around your hips anchored behind you",
            "Stand with feet shoulder-width apart facing away from the anchor",
            "Hinge at the hips against the band's resistance",
            "Drive hips forward to standing"
        ],
        "45-Degree Back Extension": [
            "Position yourself on a 45-degree back extension bench with hips at the pad edge",
            "Cross arms over chest or behind your head",
            "Lower your torso toward the floor by hinging at the hips",
            "Raise back up until your body is in line with your legs"
        ],
        "Reverse Lunge": [
            "Stand with feet hip-width apart holding a barbell on your back or dumbbells at sides",
            "Step one foot backward and lower your back knee toward the floor",
            "Drive through the front foot to return to standing",
            "Alternate legs or complete all reps on one side"
        ],
        "Deficit Lunge": [
            "Stand on a small platform or step holding dumbbells at your sides",
            "Step forward off the platform into a lunge",
            "Lower your back knee toward the floor for extended range of motion",
            "Drive through the front foot to return to the platform"
        ],
        "Curtsy Lunge": [
            "Stand with feet hip-width apart",
            "Step one foot behind and across your body in a curtsy motion",
            "Lower your back knee toward the floor",
            "Drive through the front foot to return to standing"
        ],
        "Smith Machine Hip Thrust": [
            "Set up a bench and position yourself under a Smith machine bar",
            "Place the bar across your hips with a pad",
            "Drive your hips up toward the ceiling, squeezing glutes at the top",
            "Lower with control"
        ],
        "Dumbbell Lunge": [
            "Stand holding dumbbells at your sides",
            "Step forward into a lunge, lowering your back knee toward the floor",
            "Drive through the front foot to return to standing",
            "Alternate legs"
        ],
        "Dumbbell Step-Up": [
            "Stand holding dumbbells at your sides facing a box or bench",
            "Step one foot onto the platform and drive up to standing",
            "Step back down with control",
            "Complete all reps on one side before switching"
        ],
        "Dumbbell Hip Thrust": [
            "Sit on the floor with upper back against a bench and a dumbbell on your hips",
            "Drive your hips up toward the ceiling, squeezing glutes at the top",
            "Lower with control back to the starting position"
        ],
        "Single-Leg Hip Thrust": [
            "Set up as for a hip thrust with upper back on a bench",
            "Extend one leg straight out and drive up with the working leg",
            "Squeeze glute at the top and lower with control",
            "Complete all reps on one side before switching"
        ],
        "Cable Hip Extension": [
            "Attach an ankle cuff to a low cable pulley",
            "Stand facing the machine and kick the working leg straight back",
            "Squeeze the glute at full extension",
            "Return with control"
        ],
        "Reverse Hyperextension": [
            "Lie face down on a reverse hyper machine or high bench with hips at the edge",
            "Let your legs hang down",
            "Raise your legs by extending your hips until they are in line with your torso",
            "Lower with control"
        ],
        "Glute Bridge": [
            "Lie on your back with knees bent and feet flat on the floor",
            "Drive your hips up toward the ceiling, squeezing glutes at the top",
            "Lower with control back to the floor"
        ],
        "Frog Pump": [
            "Lie on your back with the soles of your feet together and knees out",
            "Drive your hips up by squeezing your glutes",
            "Lower with control and repeat for high reps"
        ],
        "Fire Hydrant": [
            "Start on all fours with hands under shoulders and knees under hips",
            "Keeping your knee bent at 90 degrees, lift one leg out to the side",
            "Raise until your thigh is parallel to the floor",
            "Lower with control and repeat"
        ],
        "Cable Hip Adduction": [
            "Attach an ankle cuff to a low cable pulley",
            "Stand sideways to the machine with the working leg closest to the cable",
            "Pull the working leg across your body toward the midline",
            "Return with control"
        ],
        "Copenhagen Plank": [
            "Lie on your side and place the top leg on an elevated surface like a bench",
            "Lift your body off the floor, supporting with your forearm and top leg",
            "Hold the position, engaging your adductors",
            "Keep your body in a straight line"
        ],
        "Band Hip Adduction": [
            "Attach a band to a low anchor point and loop around one ankle",
            "Stand sideways and pull the banded leg across your body",
            "Control the return against the band's resistance"
        ],
        "Smith Machine Calf Raise": [
            "Stand under a Smith machine bar on a raised platform or step",
            "Place the bar on your shoulders and rise up onto your toes",
            "Hold briefly at the top, then lower your heels below the step",
            "Repeat for full range of motion"
        ],
        "Single-Leg Calf Raise": [
            "Stand on one foot on the edge of a step or platform",
            "Rise up onto your toes as high as possible",
            "Lower your heel below the step for a full stretch",
            "Complete all reps before switching legs"
        ],
        "Tibialis Raise": [
            "Stand with your back against a wall and heels about a foot away",
            "Raise your toes off the floor as high as possible",
            "Lower with control",
            "You can also use a tib raise machine if available"
        ],
        "Barbell Calf Raise": [
            "Stand holding a barbell on your back with feet hip-width apart",
            "Rise up onto your toes as high as possible",
            "Hold briefly at the top",
            "Lower with control"
        ],
        "Dumbbell Calf Raise": [
            "Stand holding dumbbells at your sides on the edge of a step",
            "Rise up onto your toes as high as possible",
            "Lower your heels below the step for a full stretch"
        ],
        "Jump Rope Calf Bounce": [
            "Jump rope staying on the balls of your feet",
            "Keep jumps small and quick, minimizing ground contact time",
            "Focus on calf engagement rather than height"
        ],
        "Calf Raise (Bodyweight)": [
            "Stand on the edge of a step or flat on the floor",
            "Rise up onto your toes as high as possible",
            "Lower with control and repeat"
        ],
        "Sit-Up": [
            "Lie on your back with knees bent and feet flat on the floor",
            "Place hands behind your head or across your chest",
            "Curl your torso all the way up to your knees",
            "Lower with control back to the floor"
        ],
        "V-Up": [
            "Lie flat on your back with arms extended overhead",
            "Simultaneously raise your legs and torso to touch your toes at the top",
            "Lower with control back to the starting position"
        ],
        "Weighted Crunch": [
            "Lie on your back with knees bent holding a weight plate on your chest",
            "Crunch up, lifting your shoulder blades off the floor",
            "Squeeze your abs at the top and lower with control"
        ],
        "Machine Crunch": [
            "Sit in the ab crunch machine with feet under the pads",
            "Grip the handles and crunch your torso forward",
            "Squeeze your abs at the bottom",
            "Return with control"
        ],
        "GHD Sit-Up": [
            "Sit on a GHD machine with feet secured and hips at the pad edge",
            "Lower your torso back until nearly parallel to the floor",
            "Use your abs and hip flexors to sit back up",
            "Touch the floor behind you for full range if possible"
        ],
        "Lying Leg Raise": [
            "Lie flat on your back with legs straight and hands under your hips",
            "Raise your legs until they are perpendicular to the floor",
            "Lower with control without letting your feet touch the floor"
        ],
        "Hanging Knee Raise": [
            "Hang from a pull-up bar with arms fully extended",
            "Raise your knees toward your chest",
            "Lower with control back to a dead hang"
        ],
        "Reverse Crunch": [
            "Lie on your back with knees bent at 90 degrees and feet off the floor",
            "Curl your hips off the floor toward your chest",
            "Lower with control back to the starting position"
        ],
        "Flutter Kick": [
            "Lie on your back with legs extended and hands under your hips",
            "Lift both legs slightly off the floor",
            "Alternate kicking legs up and down in a small range of motion",
            "Keep your lower back pressed into the floor"
        ],
        "Scissor Kick": [
            "Lie on your back with legs extended and hands under your hips",
            "Lift both legs slightly off the floor",
            "Cross legs over each other in a scissoring motion",
            "Keep your lower back pressed into the floor"
        ],
        "Captain's Chair Leg Raise": [
            "Support yourself on a captain's chair with forearms on the pads",
            "Let your legs hang straight down",
            "Raise your legs straight up in front of you",
            "Lower with control"
        ],
        "Oblique Crunch": [
            "Lie on your back with knees bent and feet flat",
            "Place hands behind your head",
            "Crunch up and rotate, bringing one elbow toward the opposite knee",
            "Lower and alternate sides"
        ],
        "Landmine Rotation": [
            "Hold the end of a landmine barbell at chest height with both hands",
            "Rotate the bar from one side to the other in an arc",
            "Keep your arms extended and rotate through your core",
            "Control the movement through the full range"
        ],
        "Cable Woodchop (High to Low)": [
            "Set a cable to the highest position with a rope or handle",
            "Stand sideways to the machine and grip with both hands",
            "Pull the cable diagonally from high to low across your body",
            "Control the return to the starting position"
        ],
        "Cable Woodchop (Low to High)": [
            "Set a cable to the lowest position with a rope or handle",
            "Stand sideways to the machine and grip with both hands",
            "Pull the cable diagonally from low to high across your body",
            "Control the return to the starting position"
        ],
        "Dumbbell Side Bend": [
            "Stand holding a dumbbell in one hand at your side",
            "Bend sideways toward the weight, then contract your obliques to return upright",
            "Complete all reps on one side before switching"
        ],
        "Windshield Wiper": [
            "Lie on your back with arms extended to the sides for support",
            "Raise your legs perpendicular to the floor",
            "Rotate your legs from side to side like a windshield wiper",
            "Keep your shoulders pressed into the floor"
        ],
        "Hollow Hold": [
            "Lie on your back with arms extended overhead and legs straight",
            "Lift your shoulders and legs off the floor, forming a slight banana shape",
            "Press your lower back into the floor and hold",
            "Maintain the position for the prescribed duration"
        ],
        "Body Saw": [
            "Start in a forearm plank with feet on sliders or a towel",
            "Shift your body forward and backward by moving through your shoulders",
            "Maintain a rigid plank position throughout",
            "Keep your core braced"
        ],
        "Stir the Pot": [
            "Place your forearms on a stability ball in a plank position",
            "Make small circles with your forearms, moving the ball",
            "Alternate clockwise and counterclockwise",
            "Keep your core tight and hips level"
        ],
        "Weighted Plank": [
            "Set up in a forearm plank position",
            "Have a partner place a weight plate on your upper back",
            "Hold the position for the prescribed duration",
            "Keep your body in a straight line"
        ],
        "Bird Dog": [
            "Start on all fours with hands under shoulders and knees under hips",
            "Simultaneously extend one arm forward and the opposite leg backward",
            "Hold briefly at full extension",
            "Return to starting position and alternate sides"
        ],
        "Bear Crawl": [
            "Start on all fours with knees hovering just above the floor",
            "Move forward by stepping opposite hand and foot simultaneously",
            "Keep your hips low and core braced",
            "Maintain a flat back throughout"
        ],
        "Neck Curl": [
            "Lie face up on a bench with your head hanging off the end",
            "Place a light plate or towel on your forehead for resistance",
            "Curl your chin toward your chest by flexing your neck",
            "Lower with control"
        ],
        "Neck Extension": [
            "Lie face down on a bench with your head hanging off the end",
            "Place a light plate on the back of your head for resistance",
            "Extend your neck upward, raising your head",
            "Lower with control"
        ],
        "Neck Lateral Flexion": [
            "Stand or sit and place your hand against the side of your head",
            "Press your head sideways against your hand's resistance",
            "Perform slowly and with control",
            "Complete all reps on one side before switching"
        ],
        "Neck Harness Extension": [
            "Wear a neck harness with weight attached",
            "Bend forward at the waist and let your head hang down",
            "Extend your neck to raise your head upward against the weight",
            "Lower with control"
        ],
        "Jefferson Deadlift": [
            "Straddle a barbell with one foot in front and one behind",
            "Grip the bar with one hand in front and one behind",
            "Stand up by extending your hips and knees",
            "Lower with control"
        ],
        "Suitcase Deadlift": [
            "Stand beside a barbell or dumbbell on the floor",
            "Grip the weight with one hand like picking up a suitcase",
            "Stand up by extending hips and knees, keeping your torso upright",
            "Lower with control"
        ],
        "Snatch": [
            "Stand over a barbell with a wide grip",
            "Pull the bar explosively from the floor to overhead in one motion",
            "Receive the bar in an overhead squat position",
            "Stand up to complete the lift"
        ],
        "Clean": [
            "Stand over a barbell with a shoulder-width grip",
            "Pull the bar explosively from the floor to the front rack position",
            "Receive the bar on your shoulders with elbows high",
            "Stand up to complete the lift"
        ],
        "Hang Clean": [
            "Hold a barbell at hip height in a standing position",
            "Hinge slightly then explosively pull the bar to the front rack",
            "Receive the bar on your shoulders with elbows high",
            "Stand up to complete the lift"
        ],
        "Hang Snatch": [
            "Hold a barbell at hip height with a wide snatch grip",
            "Hinge slightly then explosively pull the bar overhead",
            "Receive in an overhead squat position",
            "Stand up to complete the lift"
        ],
        "Clean and Jerk": [
            "Clean the barbell to your shoulders from the floor",
            "Dip your knees and drive the bar overhead with a split or push jerk",
            "Lock out the bar overhead and bring feet together",
            "Lower with control"
        ],
        "Push Jerk": [
            "Hold a barbell in the front rack position at your shoulders",
            "Dip your knees and explosively drive the bar overhead",
            "Receive the bar with a slight re-bend of the knees",
            "Stand up to lockout"
        ],
        "Muscle Snatch": [
            "Hold a barbell with a wide snatch grip at hip height",
            "Pull the bar overhead in a strict pressing motion without dropping under",
            "Keep the bar close to your body throughout",
            "Lower with control"
        ],
        "Dumbbell Snatch": [
            "Stand over a dumbbell on the floor with one hand",
            "Pull it explosively from the floor to overhead in one motion",
            "Lock out your arm at the top",
            "Lower with control and alternate sides"
        ],
        "Dumbbell Clean and Press": [
            "Stand holding dumbbells at your sides",
            "Clean the dumbbells to your shoulders with a hip drive",
            "Press them overhead to full lockout",
            "Lower with control back to your sides"
        ],
        "Kettlebell Snatch": [
            "Stand with a kettlebell between your feet",
            "Swing the kettlebell back between your legs then explosively drive it overhead",
            "Lock out at the top with arm fully extended",
            "Lower with control in one fluid motion"
        ],
        "Kettlebell Clean": [
            "Stand with a kettlebell between your feet",
            "Swing it back then explosively pull to the rack position at your shoulder",
            "The kettlebell should rest on the back of your forearm",
            "Lower with control"
        ],
        "Sled Pull": [
            "Attach a rope or straps to a loaded sled",
            "Walk backward or pull the sled toward you hand over hand",
            "Keep your core braced and maintain a low stance",
            "Reset and repeat for prescribed distance or reps"
        ],
        "Tire Flip": [
            "Squat down and grip the bottom edge of a heavy tire",
            "Drive up with your legs and hips to lift the tire",
            "As it rises, transition to pushing with your hands",
            "Flip the tire over and repeat"
        ],
        "Yoke Walk": [
            "Step under a loaded yoke and position the bar on your upper back",
            "Stand up and walk forward with controlled steps",
            "Keep your core braced and take short, quick steps",
            "Walk for the prescribed distance"
        ],
        "Trap Bar Carry": [
            "Stand inside a loaded trap bar and deadlift it up",
            "Walk forward with controlled steps holding the bar at your sides",
            "Keep your core braced and shoulders back",
            "Walk for the prescribed distance"
        ],
        "Kettlebell Goblet Squat": [
            "Hold a kettlebell by the horns at chest height",
            "Squat down until thighs are parallel or deeper",
            "Keep your elbows inside your knees and chest up",
            "Drive through your heels to stand"
        ],
        "Kettlebell Press": [
            "Clean a kettlebell to the rack position at your shoulder",
            "Press it overhead to full lockout",
            "Lower with control back to the rack position"
        ],
        "Kettlebell Row": [
            "Hinge at the hips holding a kettlebell in one hand",
            "Row the kettlebell to your hip, squeezing your back",
            "Lower with control",
            "Complete all reps before switching sides"
        ],
        "Kettlebell Deadlift": [
            "Stand with a kettlebell between your feet",
            "Hinge at the hips and grip the handle with both hands",
            "Stand up by driving your hips forward",
            "Lower with control by hinging back"
        ],
        "Kettlebell Thruster": [
            "Hold two kettlebells in the rack position at your shoulders",
            "Squat down, then drive up explosively and press overhead",
            "Lower the kettlebells back to the rack and descend into the next squat"
        ],
        "Kettlebell High Pull": [
            "Stand with a kettlebell between your feet",
            "Swing it back, then explosively pull it up to chin height with elbows high",
            "Lower with control in one fluid motion"
        ],
        "Kettlebell Windmill": [
            "Press a kettlebell overhead with one arm locked out",
            "Slowly hinge at the hip, reaching your free hand toward your foot",
            "Keep your eyes on the kettlebell and arm locked throughout",
            "Return to standing"
        ],
        "Kettlebell Halo": [
            "Hold a kettlebell upside down by the horns at chest height",
            "Circle it around your head in one direction",
            "Keep the kettlebell close to your head",
            "Alternate directions each set"
        ],
        "Double Kettlebell Swing": [
            "Stand with two kettlebells between your feet",
            "Hinge and swing both kettlebells back between your legs",
            "Drive your hips forward explosively to swing them to chest height",
            "Let them swing back and repeat"
        ],
        "Kettlebell Sumo Squat": [
            "Stand with a wide stance holding a kettlebell between your legs",
            "Squat down, keeping the kettlebell hanging between your legs",
            "Drive through your heels to stand back up"
        ],
        "Broad Jump": [
            "Stand with feet shoulder-width apart",
            "Swing your arms back and bend your knees",
            "Jump forward as far as possible, landing softly on both feet",
            "Reset and repeat"
        ],
        "Depth Jump": [
            "Stand on a box or platform",
            "Step off the box and land on both feet",
            "Immediately jump as high as possible upon landing",
            "Focus on minimizing ground contact time"
        ],
        "Jump Lunge": [
            "Start in a lunge position",
            "Jump explosively and switch legs in the air",
            "Land softly in a lunge position with the opposite leg forward",
            "Continue alternating"
        ],
        "Lateral Bound": [
            "Stand on one leg",
            "Jump laterally to the opposite foot, landing softly",
            "Immediately bound back to the starting side",
            "Focus on distance and soft landings"
        ],
        "Skater Jump": [
            "Stand on one leg",
            "Jump laterally to the opposite foot, swinging your arms across",
            "Land softly and hold briefly for balance",
            "Jump back to the other side"
        ],
        "Tuck Jump": [
            "Stand with feet shoulder-width apart",
            "Jump explosively and tuck your knees to your chest at the peak",
            "Extend your legs and land softly",
            "Reset and repeat"
        ],
        "Single-Leg Box Jump": [
            "Stand on one leg facing a box",
            "Jump off that leg and land on top of the box",
            "Step back down and repeat",
            "Complete all reps before switching legs"
        ],
        "Hurdle Hop": [
            "Set up a series of small hurdles or cones",
            "Jump over each hurdle with both feet, landing softly",
            "Minimize ground contact time between hurdles",
            "Focus on height and quick rebounds"
        ],
        "Plyo Push-Up": [
            "Start in a push-up position",
            "Lower yourself to the floor then push up explosively",
            "Your hands should leave the floor at the top",
            "Land softly and immediately descend into the next rep"
        ],
        "Medicine Ball Slam": [
            "Hold a medicine ball overhead with both hands",
            "Slam it down to the floor as hard as possible",
            "Squat down to pick it up",
            "Return to starting position and repeat"
        ],
        "Medicine Ball Chest Pass": [
            "Hold a medicine ball at chest height",
            "Explosively push the ball forward to a partner or wall",
            "Catch the return and repeat",
            "Focus on chest and arm power"
        ],
        "Medicine Ball Rotational Throw": [
            "Stand sideways to a wall holding a medicine ball at hip height",
            "Rotate your core and throw the ball against the wall",
            "Catch the rebound and rotate back",
            "Complete all reps on one side before switching"
        ],
        "Wall Ball": [
            "Hold a medicine ball at chest height facing a wall",
            "Squat down, then drive up and throw the ball to a target on the wall",
            "Catch the ball as it comes down and descend into the next squat"
        ],
        "Box Jump (Step Down)": [
            "Stand facing a box with feet shoulder-width apart",
            "Jump onto the box landing softly with both feet",
            "Step down one foot at a time instead of jumping down",
            "Reset and repeat"
        ],
        "Rowing Machine": [
            "Sit on the rowing machine and strap your feet in",
            "Grab the handle, drive with your legs first",
            "Follow through by leaning back slightly and pulling to your chest",
            "Return in reverse order: arms, body, legs"
        ],
        "Assault Bike": [
            "Sit on the bike and grip the handles",
            "Push and pull with your arms while pedaling with your legs",
            "Maintain a consistent pace or follow prescribed intervals"
        ],
        "Ski Erg": [
            "Stand facing the Ski Erg and grip the handles overhead",
            "Pull the handles down by hinging at the hips and driving with your arms",
            "Return to the starting position and repeat in a rhythmic motion"
        ],
        "Stair Climber": [
            "Stand on the stair climber and grip the handles lightly",
            "Step at a steady pace, driving through each foot",
            "Maintain an upright posture and avoid leaning on the handles"
        ],
        "Jump Rope": [
            "Hold the rope handles at hip height with elbows close to your body",
            "Swing the rope overhead and jump over it with both feet",
            "Stay on the balls of your feet with small, quick jumps",
            "Maintain a consistent rhythm"
        ],
        "Burpee": [
            "Stand with feet shoulder-width apart",
            "Drop into a squat, place hands on the floor, and kick feet back to a push-up position",
            "Perform a push-up, jump feet back to hands",
            "Explode up into a jump with arms overhead"
        ],
        "Mountain Climber": [
            "Start in a push-up position with core tight",
            "Drive one knee toward your chest",
            "Quickly switch legs, driving the other knee forward",
            "Continue alternating at a fast pace"
        ],
        "Sprint": [
            "Set up at a starting line or on a track",
            "Drive out of the start with powerful arm and leg action",
            "Run at maximum effort for the prescribed distance",
            "Decelerate gradually and walk back for recovery"
        ],
        "Sled Drag": [
            "Attach a strap to a loaded sled and hold the handles",
            "Walk backward dragging the sled behind you",
            "Maintain a low stance with core braced",
            "Cover the prescribed distance"
        ],
        "Foam Roll Quads": [
            "Lie face down with a foam roller under your thighs",
            "Roll slowly from hip to just above the knee",
            "Pause on any tender spots for 20-30 seconds",
            "Use your arms to control the pressure"
        ],
        "Foam Roll IT Band": [
            "Lie on your side with a foam roller under your outer thigh",
            "Roll from hip to just above the knee",
            "Pause on any tender spots for 20-30 seconds",
            "Use your top leg to control the pressure"
        ],
        "Foam Roll Lats": [
            "Lie on your side with a foam roller under your armpit area",
            "Roll along the length of your lat from armpit to mid-back",
            "Pause on any tender spots for 20-30 seconds"
        ],
        "Foam Roll Thoracic Spine": [
            "Lie on your back with a foam roller under your upper back",
            "Cross your arms over your chest or behind your head",
            "Roll from mid-back to upper back",
            "Extend over the roller to mobilize the thoracic spine"
        ],
        "Foam Roll Hamstrings": [
            "Sit with a foam roller under your thighs",
            "Roll from just below the glutes to above the knee",
            "Pause on any tender spots for 20-30 seconds",
            "Cross one leg over the other for more pressure"
        ],
        "Foam Roll Calves": [
            "Sit with a foam roller under your calves",
            "Roll from ankle to just below the knee",
            "Pause on any tender spots for 20-30 seconds",
            "Cross one leg over the other for more pressure"
        ],
        "Foam Roll Glutes": [
            "Sit on a foam roller with one ankle crossed over the opposite knee",
            "Lean toward the crossed side and roll over the glute",
            "Pause on any tender spots for 20-30 seconds"
        ],
        "Hip 90/90 Stretch": [
            "Sit on the floor with one leg bent at 90 degrees in front and the other at 90 degrees behind",
            "Keep your torso upright and lean forward over the front shin",
            "Hold the stretch, then switch sides",
            "Focus on opening through the hip"
        ],
        "World's Greatest Stretch": [
            "Step into a deep lunge position",
            "Place the hand opposite the front foot on the floor",
            "Rotate your torso and reach the other arm toward the ceiling",
            "Hold briefly, then switch sides"
        ],
        "Cat-Cow": [
            "Start on all fours with hands under shoulders and knees under hips",
            "Arch your back downward while lifting your head and tailbone (cow)",
            "Round your back upward while tucking your chin and tailbone (cat)",
            "Alternate slowly between positions"
        ],
        "Banded Face Pull": [
            "Attach a band at face height",
            "Pull the band apart toward your face with elbows high",
            "Squeeze your rear delts and upper back at full contraction",
            "Return with control"
        ],
        "Banded Lateral Walk": [
            "Place a band around your ankles or above your knees",
            "Stand in a quarter-squat position",
            "Step sideways maintaining tension in the band",
            "Complete prescribed steps in one direction, then return"
        ],
        "Banded Squat": [
            "Loop a band under your feet and over your shoulders or hold at chest height",
            "Squat down against the band's resistance",
            "Drive up to standing"
        ],
        "Banded Deadlift": [
            "Loop a band under your feet and over your hips or hold with hands",
            "Hinge at the hips and slightly bend knees to lower",
            "Drive hips forward to standing against band resistance"
        ],
        "Banded Push-Up": [
            "Loop a resistance band across your upper back and hold the ends under your hands",
            "Perform push-ups with the added band resistance at the top",
            "Lower with control and press up against the band"
        ],
        "Banded Row": [
            "Attach a band to a fixed point at chest height",
            "Pull the band toward your torso, squeezing your shoulder blades",
            "Return with control to full arm extension"
        ],
        "Dumbbell Squeeze Press": [
            "Lie on a flat bench pressing two dumbbells together with a neutral grip",
            "Keep the dumbbells squeezed together throughout the movement",
            "Press up to full extension maintaining inward pressure",
            "Lower to chest while keeping dumbbells in contact"
        ],
        "Behind-the-Neck Lat Pulldown": [
            "Sit at a lat pulldown station with a wide grip",
            "Pull the bar down behind your head to neck level",
            "Control the return to full extension",
            "Use lighter weight and ensure adequate shoulder mobility"
        ],
        "Prone Row": [
            "Lie face down on an incline bench with arms hanging down",
            "Hold dumbbells or a barbell and row up toward the bench",
            "Squeeze your shoulder blades at the top",
            "Lower with control"
        ],
        "Viking Press": [
            "Set up landmine handles or a Viking press attachment",
            "Stand or kneel between the handles at shoulder height",
            "Press both handles overhead to full lockout",
            "Lower with control to shoulders"
        ],
        "Smith Machine Shoulder Press": [
            "Sit on a bench inside the Smith machine with the bar at shoulder height",
            "Grip the bar slightly wider than shoulder-width",
            "Press up to full lockout",
            "Lower with control back to shoulders"
        ],
        "Lateral Raise (Cable, Behind Back)": [
            "Stand sideways to a low cable with the handle behind your back",
            "Grip the handle with the far hand reaching behind you",
            "Raise your arm out to the side to shoulder height",
            "Lower with control"
        ],
        "21s (Barbell Curl)": [
            "Hold a barbell with an underhand grip",
            "Perform 7 reps from the bottom to halfway up",
            "Then 7 reps from halfway to the top",
            "Finish with 7 full range-of-motion reps"
        ],
        "EZ-Bar Preacher Curl": [
            "Sit at a preacher bench with armpits resting on the pad",
            "Hold an EZ-bar with an underhand grip",
            "Curl the bar up toward your shoulders",
            "Lower with control to full extension"
        ],
        "Cable Concentration Curl": [
            "Sit on a bench with a low cable to one side",
            "Rest your elbow on the inside of your thigh",
            "Curl the cable handle toward your shoulder",
            "Lower with control and complete all reps before switching"
        ],
        "French Press (EZ-Bar)": [
            "Stand or sit holding an EZ-bar overhead with arms extended",
            "Lower the bar behind your head by bending at the elbows",
            "Keep your upper arms close to your head",
            "Extend back to the starting position"
        ],
        "Jefferson Squat": [
            "Straddle a barbell with one foot in front and one behind",
            "Grip the bar with one hand in front and one behind",
            "Squat down and stand back up keeping your torso upright",
            "Alternate which foot is forward between sets"
        ],
        "Hatfield Squat": [
            "Set up a safety squat bar on your back",
            "Lightly hold the rack or safety handles in front for balance",
            "Squat down to depth while using your hands for minimal support",
            "Drive up to standing"
        ],
        "ATG Split Squat": [
            "Stand in a split squat position with one foot elevated behind",
            "Lower your back knee all the way to the floor (ass to grass depth)",
            "Drive through the front foot to return to standing",
            "Focus on full range of motion through the knee"
        ],
        "Poliquin Step-Up": [
            "Stand on one foot on a 4-6 inch step",
            "Let the other foot hang off the side",
            "Lower the hanging foot by bending the working knee",
            "Return to standing, focusing on the VMO (inner quad)"
        ],
        "Sled Leg Press (Vertical)": [
            "Sit in a vertical leg press machine with feet on the platform",
            "Lower the sled by bending your knees to 90 degrees",
            "Press the sled up to full extension",
            "Do not lock out your knees fully"
        ],
        "45-Degree Hip Extension": [
            "Position yourself face down on a 45-degree hip extension machine",
            "Cross arms over chest or behind your head",
            "Lower your torso by hinging at the hips",
            "Raise back up by squeezing your glutes until body is in line with legs"
        ],
        "Banded Hip Thrust": [
            "Sit on the floor with upper back against a bench and a band across your hips",
            "Anchor the band under your feet on each side",
            "Drive your hips up toward the ceiling, squeezing glutes at the top",
            "Lower with control"
        ],
        "Smith Machine Lunge": [
            "Stand under a Smith machine bar with the bar on your upper back",
            "Step one foot forward into a lunge position",
            "Lower your back knee toward the floor",
            "Drive through the front foot to return to standing"
        ],
        "Dragon Flag": [
            "Lie on a bench and grip the edges behind your head",
            "Raise your entire body off the bench until only your upper back/shoulders remain on the bench",
            "Lower your body slowly as one rigid unit",
            "Do not let your hips bend or sag"
        ],
        "L-Sit": [
            "Support yourself on parallel bars or dip handles with arms straight",
            "Raise your legs until they are parallel to the floor",
            "Hold the position with legs straight and core engaged",
            "Maintain for the prescribed duration"
        ],
        "Suitcase Carry": [
            "Hold a heavy dumbbell or kettlebell in one hand at your side",
            "Walk forward maintaining an upright posture",
            "Resist leaning to the weighted side",
            "Walk for the prescribed distance, then switch hands"
        ],
        "Ab Wheel (Kneeling)": [
            "Kneel on the floor holding an ab wheel in front of you",
            "Roll the wheel forward, extending your body toward the floor",
            "Go as far as you can without your body touching the floor",
            "Use your abs to pull yourself back to the starting position"
        ],
        "Hanging Windshield Wiper": [
            "Hang from a pull-up bar and raise your legs up",
            "Rotate your legs from side to side like a windshield wiper",
            "Keep the movement controlled and your shoulders stable",
            "Alternate sides"
        ],
        "Man Maker": [
            "Start in a push-up position gripping two dumbbells",
            "Perform a push-up, then row each dumbbell",
            "Jump your feet to your hands and clean the dumbbells to your shoulders",
            "Press overhead, then lower and repeat"
        ],
        "Devil Press": [
            "Start standing with dumbbells at your sides",
            "Perform a burpee with hands on the dumbbells",
            "From the bottom, swing the dumbbells between your legs and overhead in one motion",
            "Lower and repeat"
        ],
        "Sandbag Clean": [
            "Stand over a sandbag with feet shoulder-width apart",
            "Squat down and grip the sandbag",
            "Explosively lift it to your chest/shoulder position",
            "Lower with control and repeat"
        ],
        "Rope Climb": [
            "Grip a climbing rope with both hands above your head",
            "Wrap the rope around one foot for a footlock",
            "Pull yourself up hand over hand, stepping up with your feet",
            "Descend with control, lowering hand over hand"
        ],
        "Prowler Push": [
            "Load the prowler sled and grip the high handles",
            "Drive forward with powerful leg strides",
            "Keep your body at a forward lean with arms extended",
            "Push for the prescribed distance"
        ],
        "Sledgehammer Swing": [
            "Stand next to a large tire holding a sledgehammer",
            "Raise the hammer overhead",
            "Swing it down forcefully onto the tire",
            "Control the rebound and repeat"
        ],
    }

    return instructions_map.get(name)

# Now build the final exercise list
final_exercises = []
matched_existing = 0
matched_free_db = 0
generated = 0

# Build section context map (## headings) and subsection map (### headings)
section_map = {}
subsection_map = {}
lines = exercise_list_md.split('\n')
current_section = ""
current_subsection = ""
for line in lines:
    if line.startswith('## ') and not line.startswith('### '):
        current_section = line.strip('# ').strip()
        current_subsection = ""
    elif line.startswith('### '):
        current_subsection = line.strip('# ').strip()
    m = re.match(r'^\s*(\d+)\.', line)
    if m:
        section_map[int(m.group(1))] = current_section
        subsection_map[int(m.group(1))] = current_subsection

for num, raw_name, is_existing in exercise_list:
    # Keep parenthetical as part of exercise name by default
    clean_name = raw_name.strip()

    # Only strip parenthetical for descriptive notes (not part of exercise name)
    # "Dumbbell Squeeze Press (close-grip DB press variation)" -> "Dumbbell Squeeze Press"
    if "close-grip DB press variation" in clean_name:
        clean_name = "Dumbbell Squeeze Press"
    # "Chin-Up Curl (Supinated narrow grip, listed under Back too)" -> "Chin-Up Curl"
    elif "listed under Back too" in clean_name:
        clean_name = "Chin-Up Curl"

    # Match to existing exercise by name, but only if:
    # 1. It's tagged [EXISTING] in the MD, OR
    # 2. The name matches AND it's not a different exercise with the same name
    #    (e.g., "Cable Kickback" is a glute exercise in original but tricep exercise in MD #138)
    section = section_map.get(num, "")

    # Special cases where same name refers to different exercise in different context
    is_different_exercise = (
        clean_name == "Cable Kickback" and "TRICEPS" in section.upper()
    )

    if clean_name in existing_by_name and not is_different_exercise:
        # Use existing exercise data exactly as-is
        final_exercises.append(existing_by_name[clean_name])
        matched_existing += 1
    else:
        # Generate new exercise entry
        section = section_map.get(num, "")

        # Try to get instructions from free-exercise-db
        free_match = fuzzy_match_free_db(clean_name)
        manual_instructions = generate_instructions(clean_name, section)

        if manual_instructions:
            instructions = manual_instructions
        elif free_match:
            cleaned = clean_instructions(free_match["instructions"])
            if cleaned:
                instructions = cleaned
                matched_free_db += 1
            else:
                instructions = [f"Perform the {clean_name} exercise with proper form"]
        else:
            instructions = [f"Perform the {clean_name} exercise with proper form"]
            generated += 1

        subsection = subsection_map.get(num, "")
        equipment = infer_equipment(clean_name, subsection)
        movement_pattern = infer_movement_pattern(clean_name)
        force_type = infer_force_type(clean_name, movement_pattern)
        body_region = infer_body_region(clean_name, section)
        laterality = infer_laterality(clean_name)
        is_compound = infer_is_compound(clean_name)

        exercise = {
            "name": clean_name,
            "aliases": generate_aliases(clean_name),
            "equipment": equipment,
            "movement_pattern": movement_pattern,
            "force_type": force_type,
            "body_region": body_region,
            "laterality": laterality,
            "is_compound": is_compound,
            "instructions": instructions,
        }

        final_exercises.append(exercise)

print(f"\nResults:")
print(f"  Total exercises: {len(final_exercises)}")
print(f"  Matched existing: {matched_existing}")
print(f"  Matched free-exercise-db instructions: {matched_free_db}")
print(f"  Generated from scratch: {generated}")

# Validate
assert len(final_exercises) == 385, f"Expected 385, got {len(final_exercises)}"

# Check all names are unique
names = [e["name"] for e in final_exercises]
dupes = [n for n in names if names.count(n) > 1]
if dupes:
    print(f"\nWARNING: Duplicate names found: {set(dupes)}")

# Validate field values
valid_equipment = {"barbell", "dumbbell", "cable", "machine", "bodyweight", "band", "kettlebell", "other"}
valid_movement = {"push", "pull", "squat", "hinge", "carry", "isolation", "other"}
valid_force = {"push", "pull", "static"}
valid_region = {"upper", "lower", "full"}
valid_laterality = {"bilateral", "unilateral"}

errors = []
for e in final_exercises:
    if e["equipment"] not in valid_equipment:
        errors.append(f"{e['name']}: invalid equipment '{e['equipment']}'")
    if e["movement_pattern"] not in valid_movement:
        errors.append(f"{e['name']}: invalid movement_pattern '{e['movement_pattern']}'")
    if e["force_type"] not in valid_force:
        errors.append(f"{e['name']}: invalid force_type '{e['force_type']}'")
    if e["body_region"] not in valid_region:
        errors.append(f"{e['name']}: invalid body_region '{e['body_region']}'")
    if e["laterality"] not in valid_laterality:
        errors.append(f"{e['name']}: invalid laterality '{e['laterality']}'")
    if not isinstance(e["is_compound"], bool):
        errors.append(f"{e['name']}: is_compound must be bool, got {type(e['is_compound'])}")
    if not e["instructions"] or len(e["instructions"]) == 0:
        errors.append(f"{e['name']}: no instructions")

if errors:
    print(f"\nValidation errors ({len(errors)}):")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\nAll exercises validated successfully!")

# Write output
output_path = DATA_DIR / "exercises.json"
with open(output_path, "w") as f:
    json.dump(final_exercises, f, indent=2)
    f.write("\n")

print(f"\nWrote {len(final_exercises)} exercises to {output_path}")
