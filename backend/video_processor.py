import os
import json
import whisper
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import subprocess
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from PIL import ImageFont
import tempfile
import shutil

from models import CaptionStyle
from config import settings


class VideoProcessor:
    def __init__(self):
        # Load Whisper model
        self.whisper_model = whisper.load_model(settings.WHISPER_MODEL)
        
    def update_video_status(self, video_id: str, status: str, error: Optional[str] = None):
        """Update video processing status."""
        metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
        
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                video_data = json.load(f)
            
            video_data["status"] = status
            
            if error:
                video_data["error"] = error
            
            if status == "completed":
                video_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            with open(metadata_path, "w") as f:
                json.dump(video_data, f, indent=2)
    
    def extract_audio(self, video_path: str, audio_path: str):
        """Extract audio from video file using FFmpeg."""
        try:
            cmd = [
                "ffmpeg", "-i", video_path,
                "-ab", "160k", "-ac", "2", "-ar", "44100",
                "-vn", audio_path, "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error extracting audio: {e}")
            return False
    
    def transcribe_audio(self, audio_path: str):
        """Transcribe audio using Whisper."""
        try:
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )
            return result
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    def create_caption_clips(self, transcription: dict, caption_style: CaptionStyle, video_duration: float):
        """Create caption clips from transcription."""
        caption_clips = []
        
        for segment in transcription["segments"]:
            text = segment["text"].strip()
            start_time = segment["start"]
            end_time = min(segment["end"], video_duration)
            
            if not text or end_time <= start_time:
                continue
            
            # Create text clip
            txt_clip = TextClip(
                text,
                fontsize=caption_style.font_size,
                color=caption_style.font_color,
                font="Arial",  # Use system default for now
                stroke_color=caption_style.stroke_color,
                stroke_width=caption_style.stroke_width
            ).set_position(('center', 'bottom')).set_start(start_time).set_end(end_time)
            
            # Add margin from bottom
            txt_clip = txt_clip.set_position(('center', video_duration * 0.85))
            
            caption_clips.append(txt_clip)
        
        return caption_clips
    
    def overlay_captions(self, video_path: str, output_path: str, transcription: dict, caption_style: CaptionStyle):
        """Overlay captions on video."""
        try:
            # Load video
            video = VideoFileClip(video_path)
            
            # Create caption clips
            caption_clips = self.create_caption_clips(transcription, caption_style, video.duration)
            
            # Composite video with captions
            if caption_clips:
                final_video = CompositeVideoClip([video] + caption_clips)
            else:
                final_video = video
            
            # Write output video
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"{output_path}.temp-audio.m4a",
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Clean up
            video.close()
            final_video.close()
            
            return True
            
        except Exception as e:
            print(f"Error overlaying captions: {e}")
            return False
    
    async def process_video(self, video_id: str, video_path: str, caption_style: CaptionStyle):
        """Process video with captions."""
        
        try:
            # Update status to processing
            self.update_video_status(video_id, "processing")
            
            # Create temporary files
            temp_audio = os.path.join(settings.TEMP_PATH, f"{video_id}.wav")
            output_video = os.path.join(settings.STORAGE_PATH, f"{video_id}_captioned.mp4")
            
            # Extract audio
            if not self.extract_audio(video_path, temp_audio):
                raise Exception("Failed to extract audio from video")
            
            # Transcribe audio
            transcription = self.transcribe_audio(temp_audio)
            if not transcription:
                raise Exception("Failed to transcribe audio")
            
            # Save transcription
            transcript_path = os.path.join(settings.STORAGE_PATH, f"{video_id}_transcript.json")
            with open(transcript_path, "w") as f:
                json.dump(transcription, f, indent=2)
            
            # Overlay captions
            if not self.overlay_captions(video_path, output_video, transcription, caption_style):
                raise Exception("Failed to overlay captions")
            
            # Update status to completed
            self.update_video_status(video_id, "completed")
            
            # Clean up temporary files
            if os.path.exists(temp_audio):
                os.unlink(temp_audio)
            
        except Exception as e:
            print(f"Error processing video {video_id}: {e}")
            self.update_video_status(video_id, "failed", str(e))
            
            # Clean up on error
            temp_audio = os.path.join(settings.TEMP_PATH, f"{video_id}.wav")
            if os.path.exists(temp_audio):
                os.unlink(temp_audio)