import httpx

from app.config import KAGGLE_KEY, KAGGLE_USERNAME, PROVIDER_TIMEOUT
from app.models.schemas import Dataset, DatasetSource

API_URL = "https://www.kaggle.com/api/v1/datasets/list"


async def search(query: str, limit: int) -> list[Dataset]:
    if not KAGGLE_USERNAME or not KAGGLE_KEY:
        raise RuntimeError("Kaggle requires KAGGLE_USERNAME and KAGGLE_KEY configuration.")
    async with httpx.AsyncClient(
        timeout=PROVIDER_TIMEOUT,
        auth=(KAGGLE_USERNAME, KAGGLE_KEY),
        follow_redirects=True,
    ) as client:
        response = await client.get(
            API_URL, params={"search": query, "pageSize": limit}
        )
        response.raise_for_status()
        payload = response.json()

    datasets = []
    for item in payload:
        ref = item.get("ref")
        if not ref:
            continue
        datasets.append(Dataset(
            id=f"kaggle:{ref}",
            name=item.get("title") or ref,
            source=DatasetSource.KAGGLE,
            description=item.get("subtitle"),
            url=f"https://www.kaggle.com/datasets/{ref}",
            license=item.get("licenseName"),
            size_bytes=item.get("totalBytes"),
            downloads=item.get("downloadCount"),
            last_updated=item.get("lastUpdated"),
            metadata={"owner": item.get("ownerName")},
        ))
    return datasets
