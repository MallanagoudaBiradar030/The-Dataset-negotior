from app.models.schemas import Dataset, TaskRequirements


def check(dataset: Dataset, requirements: TaskRequirements) -> dict:
    task = requirements.task_type
    haystack = " ".join(
        [dataset.description or "", dataset.name, dataset.data_type or "", *dataset.task_types, *dataset.features]
    ).lower()
    data_verified = bool(
        dataset.data_type and requirements.data_type
        and requirements.data_type.casefold() == dataset.data_type.casefold()
    )
    data_inferred = bool(requirements.data_type and requirements.data_type in haystack)
    task_verified = any(task in value.lower() for value in dataset.task_types) if task != "unknown" else False
    task_inferred = task != "unknown" and task in haystack
    target_name = dataset.target or dataset.metadata.get("target_col") or dataset.metadata.get("target")
    target_name = target_name or next(
        (feature for feature in dataset.features if feature.casefold() in {"label", "class", "target"}),
        None,
    )
    target_name_matches = bool(target_name)
    if requirements.target:
        requested_target_tokens = {
            token.rstrip("s")
            for token in requirements.target.casefold().split()
            if len(token) > 2
        }
        actual_target_tokens = {
            token.rstrip("s")
            for token in str(target_name or "").casefold().split()
            if len(token) > 2
        }
        target_name_matches = bool(target_name_matches and requested_target_tokens & actual_target_tokens)
    target_type = (dataset.target_type or dataset.metadata.get("target_type") or "").casefold()
    if task in {"classification", "regression"}:
        target_matches = target_name_matches
        target_type_matches = (
            target_type in {"categorical", "classlabel", "string", "bool", "boolean"}
            if task == "classification"
            else target_type in {"numeric", "number", "integer", "int", "float", "real"}
        )
    elif task == "natural language processing":
        target_matches = "text" in haystack or bool(dataset.features)
        target_type_matches = target_matches
    elif task == "computer vision":
        target_matches = "image" in haystack
        target_type_matches = target_matches
    elif task == "time series forecasting":
        target_matches = any(term in haystack for term in ("time", "date", "temporal", "sequence"))
        target_type_matches = target_matches
    else:
        target_matches = bool(dataset.features)
        target_type_matches = target_matches
    task_evidence = task_verified or task_inferred or data_verified or data_inferred
    supervised_task = task in {"classification", "regression"}
    target_type_conflict = supervised_task and bool(target_type) and not target_type_matches
    compatible = task_evidence and (
        target_matches and not target_type_conflict if supervised_task else True
    )
    verified = (task_verified or data_verified) and (
        target_matches and target_type_matches if supervised_task else True
    )
    if verified:
        details = "Provider metadata confirms task compatibility and a suitable target type."
    elif compatible:
        details = "Compatibility is inferred from provider metadata; inspect the source before use."
    elif supervised_task and not target_matches:
        details = "A matching target variable was not verified in the available metadata."
    elif target_type_conflict:
        details = "The available target metadata does not match the requested supervised task."
    else:
        details = "Available metadata does not verify compatibility with this task."
    return {
        "status": "verified" if verified else "inferred" if compatible else "uncertain",
        "compatible": compatible,
        "task_match": task_verified or task_inferred,
        "data_match": data_verified or data_inferred,
        "target_available": target_matches,
        "target_type_match": target_type_matches if supervised_task else None,
        "details": details,
    }
