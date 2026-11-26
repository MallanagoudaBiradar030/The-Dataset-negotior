import asyncio

import pytest
from fastapi import HTTPException

from app.models.schemas import Dataset, DatasetSource
from app.services import download as download_service


def test_oversized_unknown_length_download_is_rejected_before_stream_response(monkeypatch):
    class Upstream:
        status_code = 200
        headers = {}
        url = "https://archive.ics.uci.edu/static/public/sample.zip"

        def raise_for_status(self):
            return None

        async def aiter_bytes(self):
            yield b"too large"

        async def aclose(self):
            return None

    class Client:
        def __init__(self, **kwargs):
            pass

        def build_request(self, method, url):
            return url

        async def send(self, request, **kwargs):
            return Upstream()

        async def aclose(self):
            return None

    monkeypatch.setattr(download_service.httpx, "AsyncClient", Client)
    monkeypatch.setattr(download_service, "MAX_DOWNLOAD_BYTES", 2)
    dataset = Dataset(
        id="uci:1",
        name="Sample",
        source=DatasetSource.UCI,
        url="https://archive.ics.uci.edu/dataset/1/sample",
        download_url="https://archive.ics.uci.edu/static/public/sample.zip",
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(download_service.download(dataset))

    assert error.value.status_code == 413
