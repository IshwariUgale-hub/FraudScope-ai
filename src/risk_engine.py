"""
Step 4: ML PROBABILITY + BEHAVIOURAL RULES  ->  RISK SCORE + EXPLANATION.

The model alone returns a probability, which is not an explanation.  The risk
engine turns it into an analyst-facing decision:

    final score (0-100) = ML component (max 60) + rule component (max 40)

Keeping the two parts separate is deliberate:
  * the ML part captures patterns nobody wrote down,
  * the rule part is auditable and gives us the "why" sentence for free.

All weights and thresholds are prototype demonstration values, not banking
industry standards.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

ML_WEIGHT = 60.0          # max points the model can contribute
RULE_CAP = 40.0           # max points the behavioural rules can contribute

LEVELS = [(30, "LOW"), (70, "MEDIUM"), (100, "HIGH")]

ACTIONS = {
    "LOW": "Allow - no action needed.",
    "MEDIUM": "Step-up verification (OTP / app confirmation) before approving.",
    "HIGH": "Hold for additional verification and route to a fraud analyst.",
}


@dataclass
class Reason:
    signal: str
    detail: str
    points: float

    def as_dict(self):
        return asdict(self)


@dataclass
class RiskResult:
    score: int
    level: str
    action: str
    ml_probability: float
    ml_points: float
    rule_points: float
    reasons: list = field(default_factory=list)

    def as_dict(self):
        d = asdict(self)
        d["reasons"] = [r.as_dict() if isinstance(r, Reason) else r for r in self.reasons]
        return d


# --------------------------------------------------------------------------- #
# Behavioural rules
# --------------------------------------------------------------------------- #
def _rule_reasons(f: dict, txn: dict) -> list:
    """Evaluate each behavioural signal against one transaction's features."""
    reasons: list[Reason] = []
    cur = txn.get("currency", "Rs ")

    ratio = f["amount_ratio"]
    if ratio >= 3:
        pts = 8.0 if ratio < 6 else 14.0
        reasons.append(Reason(
            "Unusually high amount",
            f"{cur}{f['amount']:,.0f} is about {ratio:.1f}x this customer's usual transaction size.",
            pts))

    if f["is_new_device"]:
        reasons.append(Reason(
            "New device",
            "The transaction came from a device never used by this customer before.",
            10.0))

    if f["is_new_location"]:
        reasons.append(Reason(
            "Location deviation",
            f"Transaction originates from {txn.get('location', 'a new place')}, "
            f"outside the customer's usual locations.",
            10.0))

    if f["is_night"]:
        reasons.append(Reason(
            "Unusual transaction time",
            f"Executed at {int(f['hour']):02d}:00, inside the customer's normal inactive window.",
            8.0))

    v10 = f["txn_count_10min"]
    if v10 >= 4:
        reasons.append(Reason(
            "High transaction velocity",
            f"{int(v10)} transactions from this account within 10 minutes.",
            12.0))
    elif v10 == 3:
        reasons.append(Reason(
            "Elevated transaction velocity",
            "3 transactions within 10 minutes.",
            6.0))

    if f["seconds_since_prev"] < 60:
        reasons.append(Reason(
            "Rapid repeat transaction",
            f"Only {int(f['seconds_since_prev'])}s since the previous transaction.",
            5.0))

    if f["user_txn_index"] < 3:
        reasons.append(Reason(
            "Thin customer history",
            "Very little past activity, so behavioural baselines are weak.",
            4.0))

    return reasons


# --------------------------------------------------------------------------- #
# Combination
# --------------------------------------------------------------------------- #
def score_risk(ml_probability: float, features: dict, txn: dict | None = None) -> RiskResult:
    """Combine the model probability with the behavioural rules."""
    txn = txn or {}
    f = dict(features)
    f.setdefault("amount", txn.get("amount", 0.0))

    ml_points = round(float(ml_probability) * ML_WEIGHT, 1)
    reasons = _rule_reasons(f, txn)

    raw_rule_points = sum(r.points for r in reasons)
    rule_points = round(min(raw_rule_points, RULE_CAP), 1)
    if raw_rule_points > RULE_CAP and raw_rule_points > 0:
        # scale the displayed contributions so they add up to what was applied
        scale = RULE_CAP / raw_rule_points
        for r in reasons:
            r.points = round(r.points * scale, 1)

    score = int(round(min(ml_points + rule_points, 100)))
    level = risk_level(score)

    reasons.sort(key=lambda r: r.points, reverse=True)
    reasons.insert(0, Reason(
        "Model pattern similarity",
        f"The model rates this transaction {ml_probability:.1%} similar to known "
        f"fraudulent behaviour.",
        ml_points))

    if len(reasons) == 1 and score <= 30:
        reasons.append(Reason("No behavioural anomalies",
                              "Amount, time, device, location and velocity all match "
                              "this customer's normal pattern.", 0.0))

    return RiskResult(score=score, level=level, action=ACTIONS[level],
                      ml_probability=float(ml_probability), ml_points=ml_points,
                      rule_points=rule_points, reasons=reasons)


def risk_level(score: int) -> str:
    for upper, name in LEVELS:
        if score <= upper:
            return name
    return "HIGH"


def explain_text(result: RiskResult) -> str:
    """One-paragraph explanation for the alert feed / API response."""
    drivers = [r.signal.lower() for r in result.reasons[1:] if r.points > 0][:4]
    if not drivers:
        return f"Risk {result.score}/100 ({result.level}). No behavioural anomalies detected."
    return (f"Risk {result.score}/100 ({result.level}). Flagged because of "
            + "; ".join(drivers) + f". Recommended action: {result.action}")
