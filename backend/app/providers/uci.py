import httpx
from urllib.parse import quote

from app.config import PROVIDER_TIMEOUT
from app.models.schemas import Dataset, DatasetSource

API_URL = "https://archive.ics.uci.edu/api/datasets"


async def search(query: str, limit: int) -> list[Dataset]:
    async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(API_URL, params={"search": query, "limit": limit})
        response.raise_for_status()
        payload = response.json()

    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    items = (
        result.get("dataset", payload.get("data", []))
        if isinstance(payload, dict) else payload
    )
    datasets = []
    for item in items:
        identifier = item.get("uci_id") or item.get("id")
        name = item.get("name")
        if not identifier or not name:
            continue
        slug = quote(name.lower().replace(" ", "+"), safe="+")
        url = f"https://archive.ics.uci.edu/dataset/{identifier}/{slug}"
        datasets.append(Dataset(
            id=f"uci:{identifier}",
            name=name,
            source=DatasetSource.UCI,
            description=item.get("abstract") or item.get("description"),
            url=url,
            task_types=[item["tasks"]] if isinstance(item.get("tasks"), str) else item.get("tasks", []),
            features=[],
            license=item.get("license"),
            rows=item.get("num_instances"),
            target=item.get("target_col"),
            data_type=item.get("characteristics"),
            download_url=item.get("link"),
            metadata={"uci_id": identifier, "feature_types": item.get("feature_types")},
        ))
    return datasets
