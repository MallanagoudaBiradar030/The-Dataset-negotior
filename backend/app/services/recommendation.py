import re

from app.models.schemas import Dataset, DatasetRecommendation, ScoreFactors, TaskRequirements
from app.services.compatibility import check
from app.services.quality_analysis import analyze

WEIGHTS = {
    "task_relevance": 0.30,
    "semantic_similarity": 0.25,
    "feature_compatibility": 0.20,
    "domain_relevance": 0.15,
    "metadata_completeness": 0.10,
}
SYNONYMS = {
    "house": {"home", "housing", "property", "real"},
    "price": {"cost", "value", "pricing"},
    "image": {"photo", "picture", "visual"},
    "text": {"language", "document", "sentence"},
    "prediction": {"predict", "forecast", "estimate"},
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def recommend(dataset: Dataset, requirements: TaskRequirements) -> DatasetRecommendation:
    compatibility = check(dataset, requirements)
    quality = analyze(dataset)
    dataset_text = " ".join(
        [dataset.name, dataset.description or "", dataset.domain or "", dataset.data_type or "",
         *dataset.task_types, *dataset.features, *dataset.metadata.get("tags", [])]
    )
    request_tokens = set(requirements.keywords)
    dataset_tokens = _tokens(dataset_text)
    equivalent_tokens = request_tokens | {
        equivalent for token in request_tokens for equivalent in SYNONYMS.get(token, set())
    }
    overlap = equivalent_tokens & dataset_tokens
    semantic = min(100, 100 * len(overlap) / max(len(equivalent_tokens), 1))
    task = 100 if compatibility["status"] == "verified" else 60 if compatibility["compatible"] else 0
    requested_features = {feature.casefold() for feature in requirements.features}
    available_features = {feature.casefold() for feature in dataset.features}
    if requested_features:
        feature = 100 * len(requested_features & available_features) / len(requested_features)
    elif dataset.features and compatibility["target_available"]:
        feature = 100
    elif requirements.data_type and requirements.data_type in dataset_text.lower():
        feature = 50
    else:
        feature = 0
    domain = 100 if requirements.domain and requirements.domain in dataset_text.lower() else 50 if not requirements.domain else 0
    metadata = quality["score"]
    factors = ScoreFactors(
        task_relevance=task,
        semantic_similarity=semantic,
        feature_compatibility=feature,
        domain_relevance=domain,
        metadata_completeness=metadata,
    )
    score = round(sum(getattr(factors, key) * weight for key, weight in WEIGHTS.items()), 1)
    matched = ", ".join(sorted(overlap)[:5]) or "general dataset metadata"
    matched_requirements = []
    if compatibility["task_match"] and requirements.task_type != "unknown":
        matched_requirements.append(requirements.task_type)
    if compatibility["data_match"] and requirements.data_type:
        matched_requirements.append(f"{requirements.data_type} data")
    feature_matches = {feature.casefold() for feature in requirements.features} & {
        feature.casefold() for feature in dataset.features
    }
    if feature_matches:
        matched_requirements.append("features " + ", ".join(sorted(feature_matches)))
    satisfies = ", ".join(matched_requirements) or "some available task metadata"
    advantages = (
        "Available metadata includes " + ", ".join(
            label for label, available in (
                ("a description", bool(dataset.description)),
                ("feature information", bool(dataset.features)),
                ("a license", bool(dataset.license)),
            ) if available
        )
    )
    if advantages.endswith("includes "):
        advantages = "No additional documentation advantages could be verified"
    explanation = (
        f"Selected because it matches {satisfies} and related terms ({matched}). "
        f"{advantages}. Task compatibility is {compatibility['status']}; {quality['assessment'].lower()}. "
        "Only repository metadata was assessed, not the dataset contents."
    )
    return DatasetRecommendation(
        dataset=dataset, score=score, factors=factors, compatibility=compatibility,
        quality=quality, explanation=explanation,
    )


def rank(datasets: list[Dataset], requirements: TaskRequirements) -> list[DatasetRecommendation]:
    return sorted(
        (recommend(dataset, requirements) for dataset in datasets),
        key=lambda item: (-item.score, item.dataset.name.lower()),
    )
