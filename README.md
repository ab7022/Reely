# Reely - Automatic Video Captioning Tool

## Overview

Reely is a comprehensive video captioning application that automatically adds AI-generated captions to videos using speech-to-text transcription. The application consists of a Python FastAPI backend for video processing and a React frontend for user interaction.

## Architecture

```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────┐
│   React Frontend │ ◄─────────────────► │   FastAPI Backend │
│   - Dashboard    │                     │   - Video Processing│
│   - Auth (Firebase)                    │   - Whisper AI     │
│   - Upload UI    │                     │   - Caption Overlay │
└─────────────────┘                     └──────────────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────┐
                                         │   File Storage   │
                                         │   - Videos       │
                                         │   - Transcripts  │
                                         │   - Metadata     │
                                         └──────────────────┘
```

## Features

### Backend Features
- **Video Processing**: Upload videos or process from URLs
- **AI Transcription**: OpenAI Whisper for accurate speech-to-text
- **Caption Overlay**: Customizable styling with MoviePy
- **Async Processing**: Background task queue for video processing
- **Storage Management**: Organized file storage with metadata
- **REST API**: Complete CRUD operations for video management

### Frontend Features
- **Google Authentication**: Firebase-based user authentication
- **Dashboard**: View all processed videos with status tracking
- **Upload Interface**: Support for file upload and URL processing
- **Caption Customization**: Font, size, color, stroke, and padding options
- **Real-time Updates**: Live status updates during processing
- **Responsive Design**: Works on desktop and mobile devices

## Installation

### Prerequisites
- Python 3.9+
- Node.js 16+
- FFmpeg (required for video processing)

### FFmpeg Installation

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Configure environment variables in `.env`

6. Run the backend:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file with Firebase configuration:
```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_API_URL=http://localhost:8000
```

4. Run the frontend:
```bash
npm run dev
```

## API Documentation

### Authentication
All API endpoints require authentication via Firebase ID token in the Authorization header:
```
Authorization: Bearer <firebase_id_token>
```

### Endpoints

#### POST /api/caption
Create a new video captioning request.

**Request:**
```json
{
  "video_file": "multipart/form-data", // Optional: video file
  "video_url": "https://example.com/video.mp4", // Optional: video URL
  "font_type": "Arial",
  "font_size": 24,
  "font_color": "#FFFFFF",
  "stroke_color": "#000000",
  "stroke_width": 2,
  "padding": 10
}
```

**Response:**
```json
{
  "video_id": "uuid",
  "status": "pending",
  "message": "Video captioning request submitted"
}
```

#### GET /api/videos
Get all videos for the authenticated user.

**Response:**
```json
{
  "videos": [
    {
      "id": "uuid",
      "filename": "video.mp4",
      "status": "completed",
      "created_at": "2024-01-01T12:00:00Z",
      "completed_at": "2024-01-01T12:05:00Z",
      "captioned_video_url": "/api/download/uuid_captioned.mp4"
    }
  ]
}
```

#### GET /api/video/{video_id}
Get details for a specific video.

#### GET /api/download/{filename}
Download processed video files.

## Firebase Setup

1. Create a new Firebase project at https://console.firebase.google.com
2. Enable Google Authentication in the Authentication section
3. Add your domain to authorized domains
4. Copy the configuration to your frontend `.env.local` file

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

### Backend Deployment
The FastAPI backend can be deployed using Docker:

```bash
cd backend
docker build -t reely-backend .
docker run -p 8000:8000 reely-backend
```

### Frontend Deployment
Build and deploy the React frontend:

```bash
cd frontend
npm run build
# Deploy dist/ directory to your hosting provider
```

## Dependencies

### Backend Dependencies
- FastAPI: Web framework
- OpenAI Whisper: Speech-to-text transcription
- MoviePy: Video editing and caption overlay
- Pillow: Image processing for text rendering
- python-multipart: File upload handling
- python-firebase-admin: Firebase authentication verification
- uvicorn: ASGI server

### Frontend Dependencies
- React: UI framework
- Firebase: Authentication
- Axios: HTTP client
- Tailwind CSS: Styling
- Lucide React: Icons

## Limitations and Assumptions

- Local file storage (not suitable for production scale)
- Single-server processing (no distributed processing)
- Limited video format support (MP4, AVI, MOV)
- Maximum video file size: 100MB
- Processing time depends on video length and system resources

## Support

For issues and questions, please refer to the documentation or create an issue in the project repository.