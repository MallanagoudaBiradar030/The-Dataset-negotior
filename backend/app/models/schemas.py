from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DatasetSource(StrEnum):
    HUGGINGFACE = "Hugging Face"
    KAGGLE = "Kaggle"
    UCI = "UCI"


class TaskRequirements(BaseModel):
    description: str
    task_type: str = "unknown"
    domain: str | None = None
    features: list[str] = Field(default_factory=list)
    target: str | None = None
    data_type: str | None = None
    keywords: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    id: str
    name: str
    source: DatasetSource
    description: str | None = None
    url: str
    task_types: list[str] = Field(default_factory=list)
    domain: str | None = None
    features: list[str] = Field(default_factory=list)
    target: str | None = None
    target_type: str | None = None
    data_type: str | None = None
    license: str | None = None
    size_bytes: int | None = None
    rows: int | None = None
    downloads: int | None = None
    last_updated: str | None = None
    download_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    description: str = Field(min_length=3, max_length=2000)
    sources: list[DatasetSource] = Field(default_factory=lambda: list(DatasetSource))
    limit_per_source: int = Field(default=10, ge=1, le=50)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class ScoreFactors(BaseModel):
    task_relevance: float
    semantic_similarity: float
    feature_compatibility: float
    domain_relevance: float
    metadata_completeness: float


class DatasetRecommendation(BaseModel):
    dataset: Dataset
    score: float
    factors: ScoreFactors
    compatibility: dict[str, Any]
    quality: dict[str, Any]
    explanation: str


class SearchResponse(BaseModel):
    requirements: TaskRequirements
    results: list[DatasetRecommendation]
    providers: dict[str, str]


class CompareRequest(BaseModel):
    datasets: list[Dataset] = Field(min_length=1, max_length=5)


class CompareResponse(BaseModel):
    datasets: list[dict[str, Any]]
