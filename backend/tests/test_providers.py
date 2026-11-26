import asyncio

import pytest

from app.models.schemas import DatasetSource, SearchRequest
from app.providers import huggingface, kaggle, uci
from app.services import dataset_search


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def fake_client(monkeypatch, provider, payload):
    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse(payload)

    monkeypatch.setattr(provider.httpx, "AsyncClient", Client)


def test_huggingface_search_normalizes_live_api_metadata(monkeypatch):
    fake_client(monkeypatch, huggingface, [{
        "id": "owner/sample",
        "cardData": {
            "description": "Sample text data",
            "task_categories": ["text-classification"],
            "features": [{"name": "text"}, {"name": "label"}],
            "license": "mit",
        },
        "downloads": 24,
    }])

    result = asyncio.run(huggingface.search("sample", 5))

    assert result[0].id == "hf:owner/sample"
    assert result[0].features == ["text", "label"]
    assert result[0].downloads == 24


def test_huggingface_string_feature_metadata_is_normalized(monkeypatch):
    fake_client(monkeypatch, huggingface, [{
        "id": "owner/sample",
        "cardData": {"features": "text"},
    }])

    result = asyncio.run(huggingface.search("sample", 5))

    assert result[0].features == ["text"]


def test_kaggle_search_requires_configured_credentials(monkeypatch):
    monkeypatch.setattr(kaggle, "KAGGLE_USERNAME", None)
    monkeypatch.setattr(kaggle, "KAGGLE_KEY", None)

    with pytest.raises(RuntimeError, match="requires"):
        asyncio.run(kaggle.search("sample", 5))


def test_uci_search_normalizes_repository_api_response(monkeypatch):
    fake_client(monkeypatch, uci, {
        "result": {
            "dataset": [{
                "uci_id": 53,
                "name": "Iris",
                "abstract": "Iris flower data",
                "tasks": "Classification",
                "characteristics": "Multivariate",
                "num_instances": 150,
                "num_features": 4,
                "target_col": "class",
                "feature_types": "Real, Categorical",
                "link": "https://archive.ics.uci.edu/static/public/53/iris.zip",
            }]
        }
    })

    result = asyncio.run(uci.search("iris", 5))

    assert result[0].id == "uci:53"
    assert result[0].rows == 150
    assert result[0].target == "class"
    assert result[0].features == []
    assert result[0].download_url.endswith("/iris.zip")
    assert result[0].url == "https://archive.ics.uci.edu/dataset/53/iris"


def test_provider_failures_are_reported_independently(monkeypatch):
    async def broken(query, limit):
        raise RuntimeError("provider offline")

    async def available(query, limit):
        return []

    monkeypatch.setattr(dataset_search, "PROVIDERS", {
        DatasetSource.HUGGINGFACE: broken,
        DatasetSource.UCI: available,
    })
    request = SearchRequest(
        description="Find a classification dataset",
        sources=[DatasetSource.HUGGINGFACE, DatasetSource.UCI],
    )

    _, results, status = asyncio.run(dataset_search.search(request))

    assert results == []
    assert status[DatasetSource.HUGGINGFACE.value].startswith("unavailable")
    assert status[DatasetSource.UCI.value] == "ok (0 results)"


def test_search_returns_at_most_five_ranked_recommendations(monkeypatch):
    from app.models.schemas import Dataset

    async def many_datasets(query, limit):
        return [
            Dataset(
                id=f"uci:{number}",
                name=f"Data {number}",
                source=DatasetSource.UCI,
                description="classification data",
                url=f"https://archive.ics.uci.edu/dataset/{number}/data",
                task_types=["Classification"],
                target="label",
                target_type="categorical",
            )
            for number in range(8)
        ]

    monkeypatch.setattr(dataset_search, "PROVIDERS", {DatasetSource.UCI: many_datasets})
    request = SearchRequest(
        description="classify data",
        sources=[DatasetSource.UCI],
    )

    _, results, _ = asyncio.run(dataset_search.search(request))

    assert len(results) == 5
    assert results == sorted(results, key=lambda item: (-item.score, item.dataset.name.lower()))
