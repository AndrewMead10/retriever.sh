from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    text: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class DocumentOut(BaseModel):
    id: int
    text: str = Field(..., alias="content")
    title: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        populate_by_name = True


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)
    vector_k: Optional[int] = Field(None, ge=1, le=200)


class QueryResult(BaseModel):
    id: int
    text: str = Field(..., alias="content")
    title: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        populate_by_name = True


class QueryResponse(BaseModel):
    results: List[QueryResult]


class ImageOut(BaseModel):
    id: int
    storage_key: str
    content_type: str
    image_url: str
    metadata: Dict[str, Any]
    created_at: datetime


class ImageQueryTextRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)
    vector_k: Optional[int] = Field(None, ge=1, le=200)


class ImageQueryResult(BaseModel):
    id: int
    storage_key: str
    content_type: str
    image_url: str
    metadata: Dict[str, Any]
    created_at: datetime


class ImageQueryResponse(BaseModel):
    results: List[ImageQueryResult]
