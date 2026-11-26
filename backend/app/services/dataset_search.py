import asyncio

from app.models.schemas import DatasetSource, SearchRequest
from app.providers import huggingface, kaggle, uci
from app.services.filtering import filter_datasets
from app.services.recommendation import rank
from app.services.task_understanding import understand

PROVIDERS = {
    DatasetSource.HUGGINGFACE: huggingface.search,
    DatasetSource.KAGGLE: kaggle.search,
    DatasetSource.UCI: uci.search,
}


async def search(request: SearchRequest):
    requirements = understand(request.description)

    async def fetch(source):
        try:
            return source, await PROVIDERS[source](request.description, request.limit_per_source), None
        except Exception as exc:
            return source, [], str(exc)

    responses = await asyncio.gather(*(fetch(source) for source in request.sources))
    datasets, statuses = [], {}
    for source, results, error in responses:
        datasets.extend(results)
        statuses[source.value] = "unavailable: " + error if error else f"ok ({len(results)} results)"
    filtered = filter_datasets(datasets, request.filters, requirements)
    return requirements, rank(filtered, requirements)[:5], statuses
