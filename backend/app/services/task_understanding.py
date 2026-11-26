import re

from app.models.schemas import TaskRequirements

TASK_PATTERNS = {
    "computer vision": r"\b(images?|vision|photographs?|pictures?)\b",
    "natural language processing": r"\b(nlp|text|sentiment|language|document)\b",
    "time series forecasting": r"\b(time.?series|forecast(?:ing)?|temporal|sequence)\b",
    "classification": r"\b(classif(?:y|ication|ying)|categor(?:y|ical)|predict(?:ing)? .*category)\b",
    "regression": r"\b(regress(?:ion|ing)?|predict(?:ing)? .*price|forecast(?:ing)? .*value)\b",
    "clustering": r"\b(cluster(?:ing)?|group(?:ing)? .*similar)\b",
    "recommendation systems": r"\b(recommend(?:ation|er)?|personaliz(?:ation|ed))\b",
}
DOMAINS = {
    "housing": ["house", "housing", "real estate", "property"],
    "healthcare": ["health", "medical", "clinical", "patient", "disease"],
    "finance": ["finance", "financial", "stock", "credit"],
    "transportation": ["traffic", "transport", "vehicle", "driving"],
    "retail": ["retail", "customer", "shopping", "sales"],
}
STOP_WORDS = {
    "a", "an", "and", "for", "i", "in", "is", "it", "need", "of", "on",
    "the", "to", "using", "with", "dataset", "data", "my", "want",
}


def understand(description: str) -> TaskRequirements:
    text = description.lower()
    task_type = next((name for name, pattern in TASK_PATTERNS.items() if re.search(pattern, text)), "unknown")
    domain = next(
        (name for name, terms in DOMAINS.items() if any(term in text for term in terms)),
        None,
    )
    target_match = re.search(
        r"\b(?:predict(?:ing)?|target(?:ing)?|outcome)\s+(?:the\s+)?([a-z][a-z0-9 _-]{1,35}?)(?:\s+using|\s+from|[.,;]|$)",
        text,
    )
    feature_match = re.search(
        r"\b(?:features?|inputs?)\s+(?:such as|like|including|are|:)\s+([^.;]+)",
        text,
    )
    if not feature_match:
        feature_match = re.search(
            r"\busing\s+(.+?)(?=\s+(?:to\s+(?:predict|classify|forecast)|for\s+(?:regression|classification|clustering|forecasting))|[.;]|$)",
            text,
        )
    features = []
    if feature_match:
        excluded = {
            "classification", "classifier", "clustering", "computer vision",
            "forecasting", "natural language processing", "regression",
            "recommendation", "recommendation systems", "time series",
        }
        features = [
            feature.strip(" -")
            for feature in re.split(r",|\band\b", feature_match.group(1))
            if feature.strip(" -") and feature.strip(" -") not in excluded
        ]
    words = re.findall(r"[a-z0-9][a-z0-9_-]*", text)
    keywords = list(dict.fromkeys(word for word in words if word not in STOP_WORDS and len(word) > 2))
    data_type = (
        "image" if any(word in text for word in ("image", "photo", "picture"))
        else "text" if any(word in text for word in ("text", "nlp", "language", "sentiment"))
        else "time series" if "time series" in text or "timeseries" in text
        else "tabular" if task_type in {"classification", "regression", "clustering"}
        else None
    )
    return TaskRequirements(
        description=description,
        task_type=task_type,
        domain=domain,
        features=features,
        target=target_match.group(1).strip() if target_match else None,
        data_type=data_type,
        keywords=keywords,
    )
