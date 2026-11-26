from fastapi import APIRouter, HTTPException

from app.models.schemas import CompareRequest, CompareResponse, Dataset, SearchRequest, SearchResponse
from app.services.comparison import compare
from app.services.dataset_search import search
from app.services.download import download
from app.services.task_understanding import understand
from app.providers import huggingface, kaggle, uci

router = APIRouter(prefix="/api")
PROVIDERS = {
    "hf:": huggingface.search,
    "kaggle:": kaggle.search,
    "uci:": uci.search,
}


async def _lookup_dataset(dataset_id: str) -> Dataset:
    provider = next((search_provider for prefix, search_provider in PROVIDERS.items() if dataset_id.startswith(prefix)), None)
    if provider is None:
        raise HTTPException(404, "Dataset not found.")
    try:
        results = await provider(dataset_id.split(":", 1)[1], 10)
    except Exception as exc:
        raise HTTPException(502, "The dataset provider could not be reached.") from exc
    dataset = next((item for item in results if item.id == dataset_id), None)
    if dataset is None:
        raise HTTPException(404, "Dataset not found at its provider.")
    return dataset


@router.post("/task/understand")
async def understand_task(payload: SearchRequest):
    return understand(payload.description)


@router.post("/datasets/search", response_model=SearchResponse)
@router.post("/datasets/recommend", response_model=SearchResponse)
async def recommend_datasets(payload: SearchRequest):
    requirements, results, providers = await search(payload)
    return SearchResponse(requirements=requirements, results=results, providers=providers)


@router.post("/datasets/compare", response_model=CompareResponse)
async def compare_datasets(payload: CompareRequest):
    return CompareResponse(datasets=compare(payload.datasets))


@router.get("/datasets/{dataset_id:path}/download")
async def download_dataset(dataset_id: str):
    return await download(await _lookup_dataset(dataset_id))


@router.get("/datasets/{dataset_id:path}")
async def get_dataset(dataset_id: str):
    return await _lookup_dataset(dataset_id)


@router.post("/datasets/{dataset_id:path}/download")
async def download_from_dataset(dataset_id: str, payload: Dataset):
    if payload.id != dataset_id:
        raise HTTPException(400, "Dataset identifier does not match the request.")
    return await download(payload)
