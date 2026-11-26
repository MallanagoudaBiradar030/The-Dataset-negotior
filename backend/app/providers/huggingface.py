import httpx

from app.config import PROVIDER_TIMEOUT
from app.models.schemas import Dataset, DatasetSource

API_URL = "https://huggingface.co/api/datasets"


async def search(query: str, limit: int) -> list[Dataset]:
    async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(API_URL, params={"search": query, "limit": limit})
        response.raise_for_status()
        payload = response.json()

    datasets = []
    for item in payload:
        identifier = item.get("id")
        if not identifier:
            continue
        card = item.get("cardData") or {}
        tags = item.get("tags") or []
        features = card.get("features") or []
        if isinstance(features, str):
            features = [features]
        elif isinstance(features, dict):
            features = list(features)
        elif isinstance(features, list):
            features = [
                feature if isinstance(feature, str) else feature.get("name", "")
                for feature in features
                if isinstance(feature, str) or isinstance(feature, dict)
            ]
        else:
            features = []
        task_types = card.get("task_categories") or []
        if isinstance(task_types, str):
            task_types = [task_types]
        url = f"https://huggingface.co/datasets/{identifier}"
        datasets.append(Dataset(
            id=f"hf:{identifier}",
            name=identifier,
            source=DatasetSource.HUGGINGFACE,
            description=card.get("description"),
            url=url,
            task_types=task_types,
            domain=card.get("domain"),
            features=features,
            license=card.get("license"),
            downloads=item.get("downloads"),
            last_updated=item.get("lastModified"),
            metadata={"tags": tags},
        ))
    return datasets
