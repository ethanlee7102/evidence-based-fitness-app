"""Offline unit tests for the content-based noise filter.

Exercises `src/core/noise_filter.is_noise` — the rule that drops reference-list /
boilerplate chunks at ingestion and drove the Phase 2 corpus cleanup (1,387
chunks deleted, 98.9% precision confirmed by 15 human-agent reviewers). Pure and
deterministic: no API keys, no DB. Intentionally NOT marked `eval` so it runs in
CI under `pytest -m "not eval"`.

Each case is an anonymized shape of a real corpus chunk from that audit.
"""

from src.core.noise_filter import is_noise

# --- Real reference-list chunks: must be flagged as noise ---

REF_MDPI = (
    "Wayne, P.M.; Kiel, D.P.; Buring, J.E.; Yeh, G.Y. Impact of Tai Chi exercise on "
    "fracture-related risk factors. BMC Complement. Altern. Med. 2012, 12, 1-12. [CrossRef] "
    "Teixeira, L.E.P.; Silva, K.N.; Imoto, A.M. Progressive load training for the quadriceps. "
    "Osteoporos. Int. 2010, 21, 589-596. [CrossRef] [PubMed] "
    "Iwamoto, J.; Takeda, T.; Ichimura, S. Effect of exercise and detraining on bone. 2001."
)

REF_VANCOUVER = (
    "Wiley RL, Dunn CL, Cox RH, Hueppchen NA, Scott MS. Isometric exercise training lowers "
    "resting blood pressure. Med Sci Sports Exerc. 1992;24:749-54. "
    "Law MR, Morris JK, Wald NJ. Use of blood pressure lowering drugs in the prevention of "
    "cardiovascular disease. BMJ. 2009;338:b1665. https://doi.org/10.1136/bmj.b1665"
)


def test_reference_list_mdpi_is_noise():
    noise, reason = is_noise(REF_MDPI, "References", 40)
    assert noise is True
    assert reason in ("biblio-text", "boilerplate-section-nonprose")


def test_reference_list_vancouver_is_noise():
    noise, _ = is_noise(REF_VANCOUVER, "References", 55)
    assert noise is True


def test_reference_list_survives_mislabeled_section():
    # Docling often tags a reference list with the preceding content section.
    noise, _ = is_noise(REF_MDPI, "5. Conclusions", 44)
    assert noise is True


# --- Boilerplate: must be flagged as noise ---

def test_reference_bearing_boilerplate_section_is_noise():
    # A funding/COI-labeled chunk whose body is actually a reference list is noise.
    txt = ("This work was supported by grant 2021/00279. "
           + REF_MDPI)
    noise, _ = is_noise(txt, "FUNDING", 45)
    assert noise is True


def test_pure_publisher_disclaimer_is_tolerated_kept():
    # KNOWN, ACCEPTED behavior: a pure Frontiers/Springer disclaimer opens with
    # sentence-like prose, so the head-prose guard keeps it. These are rare, have
    # near-zero retrieval similarity to real queries, and the LLM ignores them —
    # not worth a dedicated pattern (and the FP risk that comes with it).
    txt = ("All claims expressed in this article are solely those of the authors and do not "
           "necessarily represent those of their affiliated organizations, or those of the "
           "publisher. Frontiers remains neutral with regard to jurisdictional claims.")
    noise, _ = is_noise(txt, "Publisher's note", 55)
    assert noise is False


# --- Real content: must be KEPT ---

def test_plain_content_is_kept():
    txt = ("Resistance training increases muscle hypertrophy through mechanical tension and "
           "metabolic stress. Higher loads above 60% 1RM maximize strength, while a broad range "
           "of loads can drive hypertrophy when sets are taken close to failure.")
    noise, reason = is_noise(txt, "Discussion", 5)
    assert noise is False
    assert reason == ""


def test_boundary_chunk_opening_with_prose_is_kept():
    # NUT-014 shape: section mislabeled "References" but the text opens with real prose
    # (chunk-boundary spill). The head-prose guard must protect it.
    txt = ("It is important to note that the anabolic effect of protein dosing is saturable; "
           "a ceiling of muscle protein synthesis is reached at ~0.4 g/kg per meal. Given these "
           "limits, intermittent fasting can compromise muscle growth when protein is "
           "consolidated into few meals.")
    noise, _ = is_noise(txt, "References", 60)
    assert noise is False


def test_opening_frontmatter_chunk_is_kept():
    # ROM shape: real intro sentence + MDPI first-page front-matter spliced in early.
    # The opening-front-matter guard (chunk_index <= 3) must keep it.
    txt = ("Joint range of motion (ROM) is the angle by which a joint moves from its resting "
           "position to the extremities of its motion. Citation: Afonso, J.; Ramirez-Campillo, "
           "R. Strength Training versus Stretching. Healthcare 2021, 9, 427. "
           "Publisher's Note: MDPI stays neutral with regard to jurisdictional claims. "
           "Improving ROM is a core goal for the general population and clinical contexts.")
    noise, _ = is_noise(txt, "1. Introduction", 2)
    assert noise is False


def test_frontmatter_guard_does_not_spare_late_reference_chunk():
    # The same MDPI markers in a LATE chunk (a reference list) must NOT be spared.
    txt = REF_MDPI + " Licensee MDPI, Basel, Switzerland. This article is an open access " \
                     "article distributed under the Creative Commons Attribution license."
    noise, _ = is_noise(txt, "References", 45)
    assert noise is True


def test_empty_text_is_not_noise():
    assert is_noise("", "References", 40) == (False, "")


# --- Conservative mode (ingestion): must never drop a chunk with real content ---

def test_conservative_keeps_reflist_with_trailing_conclusion():
    # Reviewer-rescued FP shape: references + a real trailing conclusion paragraph.
    txt = (REF_MDPI + " In conclusion, this meta-analysis found that compression "
           "garments and massage manage perceived fatigue, while cold water immersion and "
           "cryotherapy are the most effective modalities for reducing exercise-induced "
           "inflammation and accelerating recovery across trained populations.")
    assert is_noise(txt, "References", 40)[0] is True                    # aggressive: drop
    assert is_noise(txt, "References", 40, conservative=True)[0] is False  # ingestion: keep


def test_conservative_keeps_reflist_with_dosage_table():
    # Data-content FP shape: numbers break prose runs, so the dosage pattern rescues it.
    txt = (REF_MDPI + " Recommended dosages: creatine 3 g/day, beta-alanine 3-5 g/day, "
           "citrulline malate 8 g/day, caffeine 5-6 mg/kg, omega-3 2-3 g EPA/DHA per day.")
    assert is_noise(txt, "References", 40)[0] is True
    assert is_noise(txt, "References", 40, conservative=True)[0] is False


def test_conservative_still_drops_pure_reference_list():
    # A pure reference list (no content span) is dropped even in conservative mode.
    assert is_noise(REF_MDPI, "References", 40, conservative=True)[0] is True
    assert is_noise(REF_VANCOUVER, "References", 55, conservative=True)[0] is True
