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
for path in [
    settings.STORAGE_PATH,
    settings.UPLOADS_PATH,
    settings.TEMP_PATH,
    settings.TRANSCRIPT_CACHE_PATH,
]:
    Path(path).mkdir(parents=True, exist_ok=True)

# Verify FFmpeg availability early (non-fatal, but helpful)
try:
    import subprocess
    subprocess.run([settings.FFMPEG_BIN, "-version"], check=True, capture_output=True)
except FileNotFoundError:
    print(
        "Warning: FFmpeg not found. Set FFMPEG_BIN in .env to the full path (e.g., C:/ffmpeg/bin/ffmpeg.exe) or add it to PATH."
    )
except Exception:
    pass


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Reely API is running", "version": "1.0.0"}


@app.post("/api/caption")
async def create_caption_request(
    background_tasks: BackgroundTasks,
    video_file: Optional[UploadFile] = File(None),
    video_url: Optional[str] = Form(None),
    simulate: Optional[bool] = Form(False),
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
        "error": None,
        "steps": [
            {"key": "queued", "label": "Queued", "status": "active", "at": datetime.now(timezone.utc).isoformat()},
            {"key": "download", "label": "Download / Save", "status": "queued", "at": ""},
            {"key": "extract", "label": "Extract Audio", "status": "queued", "at": ""},
            {"key": "transcribe", "label": "Transcribe Audio", "status": "queued", "at": ""},
            {"key": "overlay", "label": "Overlay Captions", "status": "queued", "at": ""},
            {"key": "finalize", "label": "Finalize", "status": "queued", "at": ""}
        ]
    }
    
    try:
        if video_file:
            # Handle file upload
            video_metadata["source_type"] = "upload"
            video_metadata["filename"] = video_file.filename

            # Validate file size if available
            try:
                video_file.file.seek(0, os.SEEK_END)
                size = video_file.file.tell()
                video_file.file.seek(0)
                if size > settings.MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="Uploaded file is too large")
            except Exception:
                # If we cannot determine size, proceed; ffmpeg will likely fail if it's huge
                pass
            
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
            # sanitize filename (basic)
            filename = "".join(c for c in filename if c.isalnum() or c in (".", "_", "-"))
            
            video_metadata["filename"] = filename
            file_path = Path(settings.UPLOADS_PATH) / f"{video_id}_{filename}"
            
            # Download video from URL
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                response = await client.get(video_url)
                response.raise_for_status()
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
            
            video_metadata["file_path"] = str(file_path)
        
        # Update step: download/save finished
        try:
            for s in video_metadata["steps"]:
                if s["key"] == "download":
                    s["status"] = "done"
                    s["at"] = datetime.now(timezone.utc).isoformat()
                if s["key"] == "queued":
                    s["status"] = "done"
        except Exception:
            pass

        # Save metadata
        metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(video_metadata, f, indent=2)
        
        # Start background processing
        background_tasks.add_task(
            video_processor.process_video,
            video_id,
            str(file_path),
            caption_style,
            simulate or settings.SIMULATE_PROCESSING
        )
        
        return {
            "video_id": video_id,
            "status": "pending",
            "message": "Video captioning request submitted successfully",
            "simulate": simulate or settings.SIMULATE_PROCESSING
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
async def download_video(filename: str):
    """Download a processed video file (public access as requested).

    Security notes:
    - Restrict to captioned output pattern *_captioned.mp4 to avoid arbitrary file reads.
    - Ensure filename contains only safe characters.
    """
    # Basic sanitization
    safe = all(c.isalnum() or c in ("_", "-", ".") for c in filename)
    if not safe or not filename.endswith("_captioned.mp4"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    video_id = filename.split("_")[0]
    metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(settings.STORAGE_PATH).resolve() / filename
    if not file_path.exists():
        # Fallback: serve original uploaded file if captioned missing
        try:
            with open(metadata_path, "r") as f:
                video_data = json.load(f)
            original_path = video_data.get("file_path")
            if original_path and Path(original_path).exists():
                return FileResponse(path=original_path, filename=filename.replace("_captioned.mp4", Path(original_path).name), media_type="video/mp4")
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=filename, media_type="video/mp4")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)