import asyncio

import httpx

from app.main import app
from app.models.schemas import Dataset, DatasetSource
from app.api import routes


def request(method, url, json=None):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, json=json)

    return asyncio.run(send())


def test_health_endpoint():
    response = request("GET", "/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_task_understanding_endpoint():
    response = request(
        "POST",
        "/api/task/understand",
        json={"description": "Classify images of flowers"},
    )
    assert response.status_code == 200
    assert response.json()["task_type"] == "computer vision"


def test_dataset_lookup_uses_source_provider(monkeypatch):
    async def lookup(query, limit):
        return [Dataset(
            id="hf:owner/sample",
            name="Sample",
            source=DatasetSource.HUGGINGFACE,
            url="https://huggingface.co/datasets/owner/sample",
        )]

    monkeypatch.setitem(routes.PROVIDERS, "hf:", lookup)
    response = request("GET", "/api/datasets/hf:owner/sample")

    assert response.status_code == 200
    assert response.json()["id"] == "hf:owner/sample"


def test_download_rejects_untrusted_url_without_fetching():
    dataset = {
        "id": "uci:1",
        "name": "Sample",
        "source": "UCI",
        "url": "https://archive.ics.uci.edu/dataset/1/sample",
        "download_url": "http://127.0.0.1/private",
    }

    response = request("POST", "/api/datasets/uci:1/download", json=dataset)

    assert response.status_code == 400
    assert "supported provider" in response.json()["detail"]
