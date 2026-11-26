import pytest

from app.models.schemas import Dataset, DatasetSource
from app.services.compatibility import check
from app.services.filtering import filter_datasets
from app.services.quality_analysis import analyze
from app.services.recommendation import recommend
from app.services.task_understanding import understand


def dataset(**overrides):
    values = {
        "id": "uci:1", "name": "House Prices", "source": DatasetSource.UCI,
        "description": "Housing prices for regression", "url": "https://archive.ics.uci.edu/dataset/1",
        "task_types": ["Regression"], "features": ["area", "rooms"], "target": "price",
        "target_type": "numeric", "data_type": "tabular", "license": "CC BY 4.0", "rows": 100,
    }
    values.update(overrides)
    return Dataset(**values)


def test_understanding_extracts_task_domain_and_keywords():
    result = understand("I need a dataset for predicting house prices using regression")
    assert result.task_type == "regression"
    assert result.domain == "housing"
    assert "prices" in result.keywords


def test_understanding_extracts_explicit_features_without_task_noise():
    result = understand("Predict prices using area, bedrooms and bathrooms for regression")
    assert result.target == "prices"
    assert result.features == ["area", "bedrooms", "bathrooms"]


def test_recommendation_is_deterministic_and_explainable():
    requirements = understand("regression for predicting house prices")
    result = recommend(dataset(), requirements)
    assert 0 <= result.score <= 100
    assert result.factors.task_relevance == 100
    assert "regression" in result.explanation.lower()


def test_filtering_only_returns_matching_source():
    items = [dataset(), dataset(id="hf:other", source=DatasetSource.HUGGINGFACE)]
    filtered = filter_datasets(items, {"source": ["UCI"]}, understand("classification"))
    assert len(filtered) == 1
    assert filtered[0].source == DatasetSource.UCI


def test_quality_and_compatibility_disclose_metadata_limits():
    item = dataset(description=None, license=None)
    assessment = analyze(item)
    compatibility = check(item, understand("regression"))
    assert assessment["content_inspected"] is False
    assert "description not provided by source" in assessment["limitations"]
    assert compatibility["status"] == "verified"


def test_compatibility_requires_matching_target_type():
    item = dataset(target_type="categorical")
    assert check(item, understand("regression task"))["status"] == "uncertain"


def test_compatibility_checks_explicit_requested_target():
    item = dataset(target="price", target_type="numeric")
    result = check(item, understand("predict sales using regression"))
    assert result["compatible"] is False
    assert "target variable" in result["details"]


def test_feature_score_reflects_requested_feature_coverage():
    item = dataset()
    result = recommend(item, understand("regression using features such as area, bedrooms, income"))
    assert result.factors.feature_compatibility == pytest.approx(100 / 3)


def test_supervised_task_without_target_is_not_marked_compatible():
    item = dataset(target=None, task_types=["Regression"])
    result = check(item, understand("regression task"))
    assert result["status"] == "uncertain"
    assert result["compatible"] is False


def test_search_input_validation():
    from app.models.schemas import SearchRequest

    with pytest.raises(ValueError):
        SearchRequest(description="x")
