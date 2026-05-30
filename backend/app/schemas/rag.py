from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class TextContentBlock(BaseModel):
    type: Literal["text"]
    text: str = Field(..., min_length=1)


class ImageUrlContentBlock(BaseModel):
    type: Literal["image_url"]
    url: str = Field(..., min_length=1)


class ImageBase64ContentBlock(BaseModel):
    type: Literal["image_base64"]
    data: str = Field(..., min_length=1)
    media_type: str = Field(..., min_length=1)


class AudioUrlContentBlock(BaseModel):
    type: Literal["audio_url"]
    url: str = Field(..., min_length=1)


class AudioBase64ContentBlock(BaseModel):
    type: Literal["audio_base64"]
    data: str = Field(..., min_length=1)
    media_type: str = Field(..., min_length=1)


class VideoUrlContentBlock(BaseModel):
    type: Literal["video_url"]
    url: str = Field(..., min_length=1)


class VideoBase64ContentBlock(BaseModel):
    type: Literal["video_base64"]
    data: str = Field(..., min_length=1)
    media_type: str = Field(..., min_length=1)


class FileUrlContentBlock(BaseModel):
    type: Literal["file_url"]
    url: str = Field(..., min_length=1)
    media_type: Literal["application/pdf"] = "application/pdf"


class FileBase64ContentBlock(BaseModel):
    type: Literal["file_base64"]
    data: str = Field(..., min_length=1)
    media_type: Literal["application/pdf"] = "application/pdf"


ContentBlock = Annotated[
    Union[
        TextContentBlock,
        ImageUrlContentBlock,
        ImageBase64ContentBlock,
        AudioUrlContentBlock,
        AudioBase64ContentBlock,
        VideoUrlContentBlock,
        VideoBase64ContentBlock,
        FileUrlContentBlock,
        FileBase64ContentBlock,
    ],
    Field(discriminator="type"),
]


class ItemIn(BaseModel):
    title: str = Field(..., min_length=1)
    content: List[ContentBlock] = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    external_id: Optional[str] = Field(None, min_length=1)


class ItemOut(BaseModel):
    id: int
    title: str
    content: List[ContentBlock]
    metadata: Dict[str, Any]
    external_id: Optional[str] = None
    created_at: datetime

    class Config:
        populate_by_name = True


class QueryRequest(BaseModel):
    input: List[ContentBlock] = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)
    vector_k: Optional[int] = Field(None, ge=1, le=200)


class QueryResult(BaseModel):
    id: int
    title: str
    content: List[ContentBlock]
    metadata: Dict[str, Any]
    external_id: Optional[str] = None
    created_at: datetime
    score: Optional[float] = None

    class Config:
        populate_by_name = True


class QueryResponse(BaseModel):
    results: List[QueryResult]
