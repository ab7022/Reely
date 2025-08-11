import pytest
import os
import json
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from main import app
from config import settings

client = TestClient(app)

# Mock user for testing
MOCK_USER = {
    "uid": "test_user_123",
    "email": "test@example.com",
    "name": "Test User"
}

# Mock Firebase token
MOCK_TOKEN = "mock_firebase_token_for_testing"


@pytest.fixture
def mock_auth(monkeypatch):
    """Mock Firebase authentication for testing."""
    async def mock_get_current_user():
        return MOCK_USER
    
    monkeypatch.setattr("main.get_current_user", lambda: MOCK_USER)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Reely API is running"


def test_get_videos_empty(mock_auth):
    """Test getting videos when none exist."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    response = client.get("/api/videos", headers=headers)
    assert response.status_code == 200
    assert response.json()["videos"] == []


def test_caption_request_no_input(mock_auth):
    """Test caption request with no video file or URL."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    data = {
        "font_type": "Arial",
        "font_size": 24
    }
    response = client.post("/api/caption", headers=headers, data=data)
    assert response.status_code == 400
    assert "Either video_file or video_url must be provided" in response.json()["detail"]


def test_caption_request_both_inputs(mock_auth):
    """Test caption request with both video file and URL."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    
    # Create a dummy file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        tmp_file.write(b"dummy video content")
        tmp_file.flush()
        
        files = {"video_file": ("test.mp4", open(tmp_file.name, "rb"), "video/mp4")}
        data = {
            "video_url": "https://example.com/video.mp4",
            "font_type": "Arial"
        }
        
        response = client.post("/api/caption", headers=headers, files=files, data=data)
        
        # Clean up
        os.unlink(tmp_file.name)
    
    assert response.status_code == 400
    assert "Provide either video_file or video_url, not both" in response.json()["detail"]


def test_video_not_found(mock_auth):
    """Test getting a video that doesn't exist."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    response = client.get("/api/video/nonexistent_id", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"


def test_download_file_not_found(mock_auth):
    """Test downloading a file that doesn't exist."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    response = client.get("/api/download/nonexistent_file.mp4", headers=headers)
    assert response.status_code == 404


@pytest.fixture
def setup_test_video():
    """Create a test video metadata file."""
    test_video_id = "test_video_123"
    metadata = {
        "id": test_video_id,
        "user_id": MOCK_USER["uid"],
        "filename": "test_video.mp4",
        "source_type": "upload",
        "status": "completed",
        "created_at": "2024-01-01T12:00:00Z",
        "completed_at": "2024-01-01T12:05:00Z",
        "caption_style": {
            "font_type": "Arial",
            "font_size": 24,
            "font_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 2,
            "padding": 10
        },
        "error": None
    }
    
    # Ensure storage directory exists
    Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    # Write test metadata
    metadata_path = Path(settings.STORAGE_PATH) / f"{test_video_id}.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)
    
    yield test_video_id
    
    # Cleanup
    if metadata_path.exists():
        metadata_path.unlink()


def test_get_specific_video(mock_auth, setup_test_video):
    """Test getting a specific video."""
    test_video_id = setup_test_video
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    
    response = client.get(f"/api/video/{test_video_id}", headers=headers)
    assert response.status_code == 200
    
    video_data = response.json()
    assert video_data["id"] == test_video_id
    assert video_data["user_id"] == MOCK_USER["uid"]
    assert video_data["status"] == "completed"


def test_get_videos_with_data(mock_auth, setup_test_video):
    """Test getting videos when data exists."""
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    
    response = client.get("/api/videos", headers=headers)
    assert response.status_code == 200
    
    videos = response.json()["videos"]
    assert len(videos) >= 1
    assert videos[0]["user_id"] == MOCK_USER["uid"]


if __name__ == "__main__":
    pytest.main([__file__])