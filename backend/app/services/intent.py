"""Intent detection.

Milestone 1 ships a rule-based baseline behind a stable interface.
Milestone 3 replaces `predict` with a trained model (scikit-learn / PyTorch)
and reports accuracy and F1 against this baseline.
"""
import re

LABELS = ("question", "email", "summary")

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_EMAIL_WORDS = re.compile(r"\b(send|email|e-mail|mail|envoie|envoyer|envoyez|écris|ecris)\b", re.I)
_SUMMARY_WORDS = re.compile(r"\b(summar\w*|résum\w*|resum\w*|tl;dr|overview)\b", re.I)


def predict(text: str) -> str:
    if EMAIL_RE.search(text) and _EMAIL_WORDS.search(text):
        return "email"
    if _SUMMARY_WORDS.search(text):
        return "summary"
    return "question"
