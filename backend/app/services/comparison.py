from app.models.schemas import Dataset
from app.services.quality_analysis import analyze


def compare(datasets: list[Dataset]) -> list[dict]:
    fields = ("name", "source", "description", "task_types", "size_bytes", "rows", "features", "license")
    return [
        {
            **{field: getattr(dataset, field) or "Not available" for field in fields},
            "id": dataset.id,
            "url": dataset.url,
            "quality": analyze(dataset),
        }
        for dataset in datasets
    ]
