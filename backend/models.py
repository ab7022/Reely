from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CaptionStyle(BaseModel):
    font_type: str = Field(default="Arial", description="Font family")
    font_size: int = Field(default=24, ge=12, le=72, description="Font size in pixels")
    font_color: str = Field(default="#FFFFFF", description="Font color in hex format")
    stroke_color: str = Field(default="#000000", description="Stroke color in hex format")
    stroke_width: int = Field(default=2, ge=0, le=10, description="Stroke width in pixels")
    padding: int = Field(default=10, ge=0, le=50, description="Padding in pixels")


class CaptionRequest(BaseModel):
    video_url: Optional[str] = Field(None, description="URL of video to process")
    caption_style: CaptionStyle = Field(default_factory=CaptionStyle)


class VideoResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    source_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    caption_style: dict
    captioned_video_url: Optional[str] = None
    error: Optional[str] = None


class VideosResponse(BaseModel):
    videos: List[dict]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None