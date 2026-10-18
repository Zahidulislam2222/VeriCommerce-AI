"""Strict bounded input schemas; no executable content or arbitrary remote URLs."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CatalogId = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmptyBody(StrictModel):
    pass


class EvidencePolicy(StrictModel):
    api_title: ShortText
    api_service_name: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,80}$")]
    store: ShortText
    answer_method: ShortText
    draft_method: ShortText
    abstention: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    draft_heading: ShortText
    stop_words: list[ShortText] = Field(max_length=10000)
    query_expansions: dict[ShortText, list[ShortText]]


class ClaimInput(StrictModel):
    label: ShortText
    value: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    sourceId: CatalogId
    passage: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    page: Annotated[str, StringConstraints(min_length=1, max_length=40)]


class ProductInput(StrictModel):
    id: CatalogId
    parent_product_id: CatalogId | None = None
    name: ShortText
    category: str = Field(default="", max_length=100)
    subtitle: str = Field(default="", max_length=200)
    image: str = Field(default="", max_length=300, pattern=r"^(?:/[a-zA-Z0-9][a-zA-Z0-9/_.-]*)?$")
    alt: str = Field(default="", max_length=500)
    sku: str = Field(default="", max_length=100)
    color: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=4000)
    claims: list[ClaimInput] = Field(default_factory=list, max_length=50)
    status: str = Field(default="", max_length=80)
    draft: str = Field(default="", max_length=4000)


class SourceInput(StrictModel):
    id: CatalogId
    name: ShortText
    version: ShortText
    type: ShortText
    date: date


class CatalogInput(StrictModel):
    products: list[ProductInput] = Field(min_length=1, max_length=500)
    sources: list[SourceInput] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_references(self) -> CatalogInput:
        product_ids = [p.id for p in self.products]
        source_ids = [s.id for s in self.sources]
        if len(product_ids) != len(set(product_ids)) or len(source_ids) != len(set(source_ids)):
            raise ValueError("Duplicate product/source IDs")
        for product in self.products:
            for claim in product.claims:
                if claim.sourceId not in source_ids:
                    raise ValueError("Every claim must reference a supplied source")
        return self


class SearchInput(StrictModel):
    query: Annotated[str, StringConstraints(min_length=2, max_length=500, strip_whitespace=True)]
    product_id: CatalogId | None = None
    limit: int | None = Field(default=None, ge=1, le=20)


class DraftInput(StrictModel):
    product_id: CatalogId
    kind: Literal["description", "faq"] = "description"
