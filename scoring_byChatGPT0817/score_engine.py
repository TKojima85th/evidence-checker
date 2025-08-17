
"""
Unified Evidence Scoring Engine v3.0
Implements the rubric combining scientific accuracy, evidence base, expression, and completeness & safety.
"""
from typing import Dict, Any, List, Tuple
import statistics, datetime

LABEL_THRESHOLDS = [(85, "True"), (85, "Mostly True"), (60, "Mixed/Context"), (30, "Unsupported"), (0, "False")]
# We will select specific labels later; for now map >=85 to "Mostly True" by default.

def _cap(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))

def _design_rank(design: str) -> int:
    if not design:
        return 0
    d = design.lower()
    if "cochrane" in d or "systematic" in d or "meta" in d:
        return 8
    if "random" in d:
        # RCT
        if "large" in d or "multicenter" in d or "multi-centre" in d:
            return 7
        return 6
    if "prospective" in d or "cohort" in d:
        return 5
    if "case-control" in d or "case control" in d:
        return 4
    if "cross-sectional" in d or "cross sectional" in d:
        return 3
    if "case series" in d or "case report" in d:
        return 2
    if "animal" in d or "in vitro" in d:
        return 1
    if "preprint" in d:
        return 0
    # default
    return 3

def _has_rct_or_sr(studies: List[Dict[str, Any]]) -> bool:
    for s in studies:
        d = (s.get("design") or "").lower()
        if any(k in d for k in ["systematic","meta","random"]):
            return True
    return False

def _consistency(studies: List[Dict[str, Any]]) -> float:
    """Return fraction of majority direction among increase/decrease/no_increase (exclude 'mixed'/'not_reported')."""
    counts = {"increase":0, "decrease":0, "no_increase":0}
    for s in studies:
        ed = s.get("effect_direction")
        if ed in counts:
            counts[ed] += 1
    total = sum(counts.values())
    if total == 0:
        return 0.5
    return max(counts.values())/total

def _year_now() -> int:
    return datetime.datetime.now().year

def score(payload: Dict[str, Any]) -> Dict[str, Any]:
    # --- A: Scientific Accuracy (facts, causality, stats) ---
    # A1 facts
    numeric_diffs = payload.get("numeric_diffs") or []
    semantic = payload.get("semantic_exact_if_non_numeric","exact")
    if numeric_diffs:
        max_err = max(numeric_diffs)
        if max_err <= 0.02: A1 = 15
        elif max_err <= 0.05: A1 = 12
        elif max_err <= 0.10: A1 = 9
        elif max_err <= 0.20: A1 = 6
        elif max_err <= 0.30: A1 = 3
        else: A1 = 0
    else:
        A1_map = {"exact":15, "minor":12, "major":6, "wrong":0}
        A1 = A1_map.get(semantic, 6)

    # A2 causality
    claim_type = payload["claim_type"]
    alignment = payload["alignment_to_claim"]
    studies = payload.get("included_studies", [])
    has_rct_sr = _has_rct_or_sr(studies)
    if claim_type in ["intervention","diagnostic"]:
        if has_rct_sr: A2 = 15
        else: A2 = 9  # avoid causal assertion
    elif claim_type == "exposure":
        # allow 12 if quasi-experimental hinted via alignment supports & consistency high
        cons = _consistency(studies)
        if cons >= 0.7 and alignment in ["supports","partially_supports"]:
            A2 = 12
        else:
            A2 = 9
    elif claim_type in ["mechanistic","policy"]:
        A2 = 6 if alignment in ["supports","partially_supports"] else 4
    else:
        A2 = 6

    # A3 stats
    stats_flags = payload.get("stats_integrity_flags", {})
    ci = stats_flags.get("ci_present", False)
    absrisk = stats_flags.get("abs_risk_present", False)
    confuse = stats_flags.get("rr_abs_confused", False)
    unit_err = stats_flags.get("unit_errors", False)
    A3 = 10
    if not ci: A3 -= 2
    if not absrisk: A3 -= 3
    if confuse: A3 -= 3
    if unit_err: A3 -= 2
    A3 = _cap(A3, 0, 10)

    # Cap by alignment & GRADE
    cap_A = 40
    grade = payload["GRADE_certainty"]
    cap_applied_A = False
    if alignment in ["contradicts","insufficient"] and grade in ["high","moderate"]:
        A1, A2, A3 = min(A1,6), min(A2,6), min(A3,4)
        cap_A = min(cap_A, 20); cap_applied_A = True
    if grade == "very_low":
        cap_A = min(cap_A, 20); cap_applied_A = True
    A_total = min(cap_A, A1 + A2 + A3)

    # --- B: Evidence Base ---
    # B1 quality (take the best-ranked design present)
    best_rank = 0
    for s in studies:
        if s.get("retraction_status") in ["retracted","expression_of_concern"]:
            # keep rank but will penalize later
            pass
        best_rank = max(best_rank, _design_rank(s.get("design","")))
    # Map rank to points (0..15)
    rank_to_points = {8:15, 7:13, 6:11, 5:9, 4:7, 3:7, 2:5, 1:3, 0:1}
    B1 = rank_to_points.get(best_rank, 0)

    # Cap B1 if no RCT/SR for intervention/diagnostic
    cap_applied_B = False
    if payload["claim_type"] in ["intervention","diagnostic"] and not has_rct_sr:
        B1 = min(B1, 11); cap_applied_B = True

    # B2 appropriateness + verifiability + recency
    # Appropriateness heuristic: directness if outcomes present and alignment not "insufficient"
    appropriateness = 6 if (len(studies)>0 and any((s.get("primary_outcomes") for s in studies)) and alignment!="insufficient") else (4 if len(studies)>0 else 2)
    # Verifiability
    ver_rate = float(payload.get("citation_verifiability_rate",0))
    ver_score = 2 if ver_rate >= 0.8 else (1 if ver_rate >= 0.3 else 0)
    # Recency
    current_year = datetime.datetime.now().year
    key_year = payload.get("newest_key_evidence_year", current_year-20)
    # Guidelines
    guide_year = payload.get("guideline_year", None)
    rec_score = 0
    if key_year >= current_year - 10: rec_score += 1
    elif key_year >= current_year - 15: rec_score += 0
    else: rec_score += 0
    if guide_year is not None:
        if guide_year >= current_year - 5: rec_score += 1
        elif guide_year >= current_year - 8: rec_score += 0
        else: rec_score += 0
    B2 = int(appropriateness + ver_score + rec_score)
    if B2 > 10: B2 = 10

    B_total = B1 + B2

    # --- C: Expression ---
    # C1 certainty tone
    grade_map = {"high":10, "moderate":9, "low":8, "very_low":7}
    base_tone = grade_map.get(grade, 8)
    tone = base_tone + int(payload.get("language_assertiveness_score",0))
    C1 = _cap(tone, 0, 10)

    # C2 avoid exaggeration
    ex_level = int(payload.get("exaggeration_level",0)) # 0 best, 5 worst
    C2 = {0:10,1:8,2:6,3:4,4:2,5:0}.get(ex_level, 6)

    C_total = C1 + C2

    # --- D: Completeness & Safety ---
    comp = payload.get("completeness_checks", {})
    covered = sum(1 for k in ["targets","dose","effect","harms","contraind","heterogeneity"] if comp.get(k, False))
    D1 = {6:7,5:6,4:4,2:2}.get(covered, 0)

    bal = payload.get("balance_flags", {})
    if bal.get("mentions_counterevidence", False) and not bal.get("bias_to_benefit", False):
        D2 = 4
    elif bal.get("mentions_counterevidence", False):
        D2 = 3
    elif bal.get("bias_to_benefit", False):
        D2 = 1
    else:
        D2 = 0

    saf = payload.get("safety_flags", {})
    saf_points = 0
    if saf.get("adverse_events_quantified", False): saf_points += 2
    elif any(saf.get(k, False) for k in ["adverse_events_quantified"]): pass
    if saf.get("high_risk_groups", False): saf_points += 1
    if saf.get("clinical_guidance", False): saf_points += 1
    D3 = min(4, saf_points)

    D_total = D1 + D2 + D3

    base = int(A_total + B_total + C_total + D_total)

    # --- Bonus ---
    bonus_flags = payload.get("bonus_flags", {})
    bonus = 0
    bonus_items = []
    if bonus_flags.get("uncertainty_transparency",0) > 0:
        pts = min(3, int(bonus_flags["uncertainty_transparency"])); bonus += pts; bonus_items.append({"type":"uncertainty_transparency","points":pts})
    if bonus_flags.get("nnt_nnh",0) > 0:
        pts = min(3, int(bonus_flags["nnt_nnh"])); bonus += pts; bonus_items.append({"type":"nnt_nnh","points":pts})
    if bonus_flags.get("external_validation",0) > 0:
        pts = min(2, int(bonus_flags["external_validation"])); bonus += pts; bonus_items.append({"type":"external_validation","points":pts})
    if bonus_flags.get("triangulation",0) > 0:
        pts = min(2, int(bonus_flags["triangulation"])); bonus += pts; bonus_items.append({"type":"triangulation","points":pts})
    bonus = min(10, bonus)

    # --- Penalties ---
    p = payload.get("penalties_flags", {})
    penalties = 0
    penalty_items = []
    def add_pen(name, pts):
        nonlocal penalties, penalty_items
        penalties += abs(pts); penalty_items.append({"type":name, "points":-abs(pts)})

    # major
    if p.get("fabricated", False):
        add_pen("fabricated", 100)
    if p.get("retracted_as_major", False) or p.get("predatory_major", False):
        add_pen("retracted_or_predatory_major", 50)
    if p.get("major_safety_omission", False):
        add_pen("major_safety_omission", 15)
    # medium
    if p.get("causation_misuse", False):
        add_pen("causation_misuse", 10)
    if p.get("cherry_pick", False):
        add_pen("cherry_pick", 10)
    if p.get("guideline_misquote", False):
        add_pen("guideline_misquote", 7)
    if p.get("too_old_only", False):
        add_pen("too_old_only", 6)
    # minor
    if p.get("scale_exaggeration", False):
        add_pen("scale_exaggeration", 4)
    if p.get("term_misuse", False):
        add_pen("term_misuse", 3)
    if p.get("overgeneralization", False):
        add_pen("overgeneralization", 3)
    if p.get("fear_appeal", False):
        add_pen("fear_appeal", 2)

    # forced caps when major penalties
    capA = capB = False
    if p.get("retracted_as_major", False) or p.get("predatory_major", False):
        # lower caps
        capA = True
        if A_total > 20:
            A_total = 20
        if B1 > 7:
            B1 = 7
            B_total = B1 + B2
        base = int(A_total + B_total + C_total + D_total)

    if p.get("fabricated", False):
        total_score = 0
        label = "False"
        confidence = "high"
        return {
          "score_breakdown": {
            "A_scientific_accuracy": {"facts": A1, "causality": A2, "stats": A3, "cap_applied": cap_applied_A or capA, "subtotal": int(A_total)},
            "B_evidence_base": {"quality": B1, "appropriateness_verifiability_recency": int(B2), "cap_applied": cap_applied_B or capB, "subtotal": int(B_total)},
            "C_expression": {"certainty_tone": int(C1), "no_exaggeration": int(C2), "subtotal": int(C_total)},
            "D_completeness_safety": {"coverage": int(D1), "balance": int(D2), "safety": int(D3), "subtotal": int(D_total)}
          },
          "base": int(base),
          "bonus": bonus_items,
          "penalties": penalty_items,
          "total_score": int(total_score),
          "label": label,
          "confidence": confidence
        }

    total = max(0, min(100, base + bonus - penalties))

    # Label
    if total >= 90:
        label = "True"
    elif total >= 85:
        label = "Mostly True"
    elif total >= 60:
        label = "Mixed/Context"
    elif total >= 30:
        label = "Unsupported"
    elif total >= 10:
        label = "Misleading"
    else:
        label = "Harmful"

    # Confidence
    cons = _consistency(studies)
    ver = float(payload.get("citation_verifiability_rate",0))
    if grade in ["high","moderate"] and cons >= 0.7 and ver >= 0.8:
        confidence = "high"
    elif grade in ["low","very_low"] or cons < 0.5 or ver < 0.3:
        confidence = "low"
    else:
        confidence = "medium"

    return {
      "score_breakdown": {
        "A_scientific_accuracy": {"facts": int(A1), "causality": int(A2), "stats": int(A3), "cap_applied": cap_applied_A, "subtotal": int(A_total)},
        "B_evidence_base": {"quality": int(B1), "appropriateness_verifiability_recency": int(B2), "cap_applied": cap_applied_B, "subtotal": int(B_total)},
        "C_expression": {"certainty_tone": int(C1), "no_exaggeration": int(C2), "subtotal": int(C_total)},
        "D_completeness_safety": {"coverage": int(D1), "balance": int(D2), "Safety": int(D3), "subtotal": int(D_total)}
      },
      "base": int(base),
      "bonus": bonus_items,
      "penalties": penalty_items,
      "total_score": int(total),
      "label": label,
      "confidence": confidence
    }
