"""Strict contracts for bounded ingestion, retrieval inspection and human review."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from .models import CatalogId, ShortText, StrictModel

Method = Literal["keyword", "dense", "hybrid", "rerank"]


class UploadInput(StrictModel):
    product_id: CatalogId | None = None
    source_id: CatalogId
    filename: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_. -]{0,159}$")]
    media_type: ShortText
    content_base64: str = Field(min_length=4, max_length=22369624)
    version: ShortText


class ContextInput(StrictModel):
    query: str = Field(min_length=2, max_length=500)
    product_id: CatalogId | None = None
    method: Method = "hybrid"
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=1, max_length=40)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    budget_chars: int | None = Field(default=None, ge=100, le=50000)


class SnapshotInput(StrictModel):
    product_id: CatalogId | None = None


class RelationInput(StrictModel):
    subject_id: CatalogId
    predicate: Literal["compatible_with", "documented_by", "has_variant", "supported_by"]
    object_id: CatalogId
    revision_id: UUID


class ImageReviewInput(StrictModel):
    upload_id: UUID
    purpose: Literal["decorative", "functional", "informative"]
    observation: str = Field(default="", max_length=1000)
    alt: str = Field(default="", max_length=500)
    function: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def purpose_contract(self) -> ImageReviewInput:
        if self.purpose == "decorative" and self.alt:
            raise ValueError("Decorative images require empty alternative text")
        if self.purpose != "decorative" and not self.alt:
            raise ValueError("Informative and functional images require alternative text")
        if self.purpose == "functional" and not self.function:
            raise ValueError("Functional images require a stated action or destination")
        return self


class BenchmarkReviewInput(StrictModel):
    dataset_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    question_ids: list[ShortText] = Field(default_factory=list, max_length=200)
    image_ids: list[ShortText] = Field(default_factory=list, max_length=120)
    decision: Literal["approved", "needs_changes"]
    notes: str = Field(default="", max_length=2000)


class IntelligencePolicy(StrictModel):
    version: ShortText
    schema_context: str = Field(min_length=1, max_length=200)
    schema_availability: list[ShortText]
    offer_labels: list[ShortText]
    non_scalar_labels: list[ShortText]
    relation_labels: dict[str, str]
    draft_formats: dict[str, str]
    unsafe_claim_terms: list[ShortText]
    unit_aliases: dict[str, str]
    unit_factors: dict[str, tuple[str, float]]
    csv_columns: list[ShortText]
    media_types: list[ShortText]
    image_observation_notice: str
    benchmark_notice: str
    reranker: dict[str, str | float]
    context: dict[str, str | int]
