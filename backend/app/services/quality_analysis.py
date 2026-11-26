from app.models.schemas import Dataset


def analyze(dataset: Dataset) -> dict:
    checks = {
        "description": bool(dataset.description),
        "license": bool(dataset.license),
        "features": bool(dataset.features),
        "data_format": bool(dataset.data_type or dataset.metadata.get("tags")),
        "size": dataset.size_bytes is not None or dataset.rows is not None,
        "task_metadata": bool(dataset.task_types or dataset.target),
        "source_link": bool(dataset.url),
    }
    known = sum(checks.values())
    score = round(100 * known / len(checks))
    return {
        "score": score,
        "indicators": checks,
        "assessment": "Well documented" if score >= 70 else "Some metadata is missing" if score >= 40 else "Limited metadata available",
        "limitations": [f"{key.replace('_', ' ')} not provided by source" for key, present in checks.items() if not present],
        "content_inspected": False,
    }
