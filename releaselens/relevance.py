"""Optional relevance-logit gate. Relevance is neither entailment nor probability."""

import json
import math
import os
import re
from pathlib import Path

MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


class RelevanceScorer:
    """Already scoped query/passage pairs only; no model-side permission decisions."""

    def __init__(self):
        from sentence_transformers import CrossEncoder
        from torch.nn import Identity

        self.activation = Identity()
        self.name = f"{MODEL}@{REVISION}"
        self.model = CrossEncoder(
            MODEL,
            revision=REVISION,
            trust_remote_code=False,
            device="cpu",
            max_length=256,
            activation_fn=self.activation,
        )

    def score(self, question, passages):
        if len(passages) > 20:
            raise ValueError("At most twenty already authorized candidates")
        if not passages:
            return []
        values = self.model.predict(
            [(question, p.section + "\n" + p.text) for p in passages],
            batch_size=8,
            show_progress_bar=False,
            activation_fn=self.activation,
        ).tolist()
        if len(values) != len(passages) or any(not math.isfinite(float(v)) for v in values):
            raise RuntimeError("Expected one finite relevance logit per passage")
        return [float(v) for v in values]


class RelevanceGate:
    def __init__(self, scorer, threshold, policy_id="experimental"):
        if not math.isfinite(threshold):
            raise ValueError("Finite threshold required")
        self.scorer, self.threshold, self.policy_id = scorer, threshold, policy_id

    def filter(self, question, rows):
        if not rows:
            return [], {"policy": self.policy_id, "accepted": False, "score": None}
        scores = self.scorer.score(question, [p for p, _, _ in rows])
        if len(scores) != len(rows) or any(not math.isfinite(float(v)) for v in scores):
            raise RuntimeError("Invalid relevance scores")
        best = max(range(len(rows)), key=lambda i: (scores[i], -i))
        accepted = scores[best] >= self.threshold
        return ([rows[best]] if accepted else []), {
            "policy": self.policy_id,
            "model": self.scorer.name,
            "threshold_raw_logit": self.threshold,
            "score": scores[best],
            "accepted": accepted,
            "meaning": "Experimental relevance filter; not calibrated confidence or semantic support",
        }


def configured_gate():
    path = os.getenv("ANSWERABILITY_POLICY")
    if not path:
        return None
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        policy["model"] != f"{MODEL}@{REVISION}"
        or policy["retrieval_mode"] != "version"
        or policy["k"] != 4
    ):
        raise ValueError("Incompatible answerability policy")
    if not re.fullmatch("[a-f0-9]{64}", policy["dataset_sha256"]):
        raise ValueError("Policy must name its frozen calibration dataset")
    return RelevanceGate(RelevanceScorer(), float(policy["threshold"]), policy["policy_id"])
