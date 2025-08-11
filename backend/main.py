from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
from pathlib import Path
import json
from datetime import datetime, timezone
import uuid
from typing import Optional, List
import shutil
import httpx

from auth import verify_firebase_token, get_current_user
from video_processor import VideoProcessor
from models import CaptionRequest, VideoResponse, VideosResponse, CaptionStyle
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Reely API",
    description="Automatic Video Captioning Tool",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize video processor
video_processor = VideoProcessor()
security = HTTPBearer()

# Ensure required directories exist
for path in [settings.STORAGE_PATH, settings.UPLOADS_PATH, settings.TEMP_PATH]:
    Path(path).mkdir(parents=True, exist_ok=True)


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Reely API is running", "version": "1.0.0"}


@app.post("/api/caption")
async def create_caption_request(
    background_tasks: BackgroundTasks,
    video_file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    font_type: str = Form("Arial"),
    font_size: int = Form(24),
    font_color: str = Form("#FFFFFF"),
    stroke_color: str = Form("#000000"),
    stroke_width: int = Form(2),
    padding: int = Form(10),
    current_user: dict = Depends(get_current_user)
):
    """Create a new video captioning request."""
    
    if not video_file and not video_url:
        raise HTTPException(status_code=400, detail="Either video_file or video_url must be provided")
    
    if video_file and video_url:
        raise HTTPException(status_code=400, detail="Provide either video_file or video_url, not both")
    
    # Create video ID and metadata
    video_id = str(uuid.uuid4())
    
    # Create caption style
    caption_style = CaptionStyle(
        font_type=font_type,
        font_size=font_size,
        font_color=font_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        padding=padding
    )
    
    # Create video metadata
    video_metadata = {
        "id": video_id,
        "user_id": current_user["uid"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "caption_style": caption_style.model_dump(),
        "completed_at": None,
        "error": None
    }
    
    try:
        if video_file:
            # Handle file upload
            video_metadata["source_type"] = "upload"
            video_metadata["filename"] = video_file.filename
            
            # Save uploaded file
            file_path = Path(settings.UPLOADS_PATH) / f"{video_id}_{video_file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(video_file.file, buffer)
            
            video_metadata["file_path"] = str(file_path)
            
        else:
            # Handle URL download
            video_metadata["source_type"] = "url"
            video_metadata["video_url"] = video_url
            
            # Extract filename from URL
            filename = video_url.split("/")[-1]
            if not filename or "." not in filename:
                filename = f"{video_id}.mp4"
            
            video_metadata["filename"] = filename
            file_path = Path(settings.UPLOADS_PATH) / f"{video_id}_{filename}"
            
            # Download video from URL
            async with httpx.AsyncClient() as client:
                response = await client.get(video_url)
                response.raise_for_status()
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
            
            video_metadata["file_path"] = str(file_path)
        
        # Save metadata
        metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(video_metadata, f, indent=2)
        
        # Start background processing
        background_tasks.add_task(
            video_processor.process_video,
            video_id,
            str(file_path),
            caption_style
        )
        
        return {
            "video_id": video_id,
            "status": "pending",
            "message": "Video captioning request submitted successfully"
        }
        
    except Exception as e:
        # Clean up on error
        if 'file_path' in locals() and Path(file_path).exists():
            Path(file_path).unlink()
        
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/api/videos", response_model=VideosResponse)
async def get_videos(current_user: dict = Depends(get_current_user)):
    """Get all videos for the current user."""
    
    videos = []
    storage_path = Path(settings.STORAGE_PATH)
    
    for metadata_file in storage_path.glob("*.json"):
        try:
            with open(metadata_file, "r") as f:
                video_data = json.load(f)
            
            # Filter by user
            if video_data.get("user_id") == current_user["uid"]:
                # Add download URL if completed
                if video_data["status"] == "completed":
                    output_filename = f"{video_data['id']}_captioned.mp4"
                    video_data["captioned_video_url"] = f"/api/download/{output_filename}"
                
                videos.append(video_data)
        except Exception:
            continue
    
    # Sort by creation date (newest first)
    videos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return VideosResponse(videos=videos)


@app.get("/api/video/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, current_user: dict = Depends(get_current_user)):
    """Get details for a specific video."""
    
    metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
    
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    with open(metadata_path, "r") as f:
        video_data = json.load(f)
    
    # Check if user owns this video
    if video_data.get("user_id") != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add download URL if completed
    if video_data["status"] == "completed":
        output_filename = f"{video_data['id']}_captioned.mp4"
        video_data["captioned_video_url"] = f"/api/download/{output_filename}"
    
    return VideoResponse(**video_data)


@app.get("/api/download/{filename}")
async def download_video(filename: str, current_user: dict = Depends(get_current_user)):
    """Download a processed video file."""
    
    # Extract video ID from filename
    video_id = filename.split("_")[0]
    
    # Verify user owns this video
    metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
    
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    with open(metadata_path, "r") as f:
        video_data = json.load(f)
    
    if video_data.get("user_id") != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if file exists
    file_path = Path(settings.STORAGE_PATH) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)