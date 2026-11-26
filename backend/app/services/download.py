import re
import tempfile
from urllib.parse import urljoin
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.config import KAGGLE_KEY, KAGGLE_USERNAME, MAX_DOWNLOAD_BYTES
from app.models.schemas import Dataset, DatasetSource


async def download(dataset: Dataset) -> StreamingResponse:
    if dataset.source == DatasetSource.KAGGLE:
        if not KAGGLE_USERNAME or not KAGGLE_KEY:
            raise HTTPException(503, "Kaggle downloads require KAGGLE_USERNAME and KAGGLE_KEY.")
        reference = dataset.id.removeprefix("kaggle:")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", reference):
            raise HTTPException(400, "Invalid Kaggle dataset identifier.")
        url = f"https://www.kaggle.com/api/v1/datasets/download/{reference}"
        auth = (KAGGLE_USERNAME, KAGGLE_KEY)
    elif dataset.download_url:
        url = dataset.download_url
        auth = None
    else:
        raise HTTPException(501, "This provider does not expose a supported direct download for this dataset.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.kaggle.com", "huggingface.co", "archive.ics.uci.edu"}:
        raise HTTPException(400, "Download URL is not from a supported provider.")

    client = httpx.AsyncClient(follow_redirects=False, timeout=30)
    try:
        upstream = await client.send(client.build_request("GET", url), auth=auth, stream=True)
        for _ in range(3):
            if upstream.status_code not in {301, 302, 303, 307, 308}:
                break
            location = upstream.headers.get("location")
            redirected_url = urljoin(str(upstream.url), location or "")
            redirected_host = urlparse(redirected_url).hostname
            if urlparse(redirected_url).scheme != "https" or redirected_host not in {
                "www.kaggle.com", "storage.googleapis.com", "archive.ics.uci.edu",
                "huggingface.co", "cdn-lfs.huggingface.co", "cas-bridge.xethub.hf.co",
            }:
                raise HTTPException(502, "Provider redirected to an unsupported download host.")
            await upstream.aclose()
            upstream = await client.send(client.build_request("GET", redirected_url), stream=True)
        upstream.raise_for_status()
    except HTTPException:
        await client.aclose()
        raise
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(502, "The provider could not deliver this dataset download.") from exc
    length = upstream.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_DOWNLOAD_BYTES:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(413, "Dataset exceeds the 100 MB download limit.")
    media_type = upstream.headers.get("content-type", "application/octet-stream")
    filename = re.sub(r"[^A-Za-z0-9._-]", "-", dataset.id)[:100] or "dataset"
    buffered = tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    count = 0
    try:
        async for chunk in upstream.aiter_bytes():
            count += len(chunk)
            if count > MAX_DOWNLOAD_BYTES:
                await upstream.aclose()
                await client.aclose()
                buffered.close()
                raise HTTPException(413, "Dataset exceeds the 100 MB download limit.")
            buffered.write(chunk)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        buffered.close()
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(502, "The provider interrupted this dataset download.") from exc
    finally:
        await upstream.aclose()
        await client.aclose()
    buffered.seek(0)

    def chunks():
        try:
            while chunk := buffered.read(64 * 1024):
                yield chunk
        finally:
            buffered.close()

    return StreamingResponse(
        chunks(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.zip"'},
    )
