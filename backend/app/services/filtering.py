from app.models.schemas import Dataset, TaskRequirements


def filter_datasets(datasets: list[Dataset], filters: dict[str, list[str]], requirements: TaskRequirements) -> list[Dataset]:
    filtered = datasets
    for key, values in filters.items():
        normalized = {value.casefold() for value in values}
        if key == "source":
            filtered = [item for item in filtered if item.source.value.casefold() in normalized]
        elif key == "task":
            filtered = [item for item in filtered if any(task.casefold() in normalized for task in item.task_types)]
        elif key == "domain":
            filtered = [item for item in filtered if (item.domain or "").casefold() in normalized]
        elif key == "license":
            filtered = [item for item in filtered if (item.license or "").casefold() in normalized]
        elif key == "data_type":
            filtered = [item for item in filtered if (item.data_type or "").casefold() in normalized]
        elif key == "availability":
            filtered = [item for item in filtered if ("download" if item.download_url else "view") in normalized]
    return filtered
