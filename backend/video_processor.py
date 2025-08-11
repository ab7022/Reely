import os
import json
try:
    import whisper  # type: ignore
except Exception:
    whisper = None
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple
import asyncio
import subprocess
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import shutil
import hashlib

from models import CaptionStyle
from config import settings


class VideoProcessor:
    def __init__(self):
        # Load Whisper model
        try:
            if whisper is not None:
                self.whisper_model = whisper.load_model(settings.WHISPER_MODEL)
            else:
                self.whisper_model = None
        except Exception as e:
            print(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
        
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

    def _update_step(self, video_id: str, key: str, status: str):
        """Update a specific step's status and timestamp."""
        metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
        if not metadata_path.exists():
            return
        try:
            with open(metadata_path, "r") as f:
                video_data = json.load(f)
            steps = video_data.get("steps", [])
            now = datetime.now(timezone.utc).isoformat()
            for s in steps:
                if s.get("key") == key:
                    s["status"] = status
                    s["at"] = now
                # Move active flag to current step
                if status == "active":
                    if s.get("key") != key and s.get("status") == "active":
                        s["status"] = "done"
            video_data["steps"] = steps
            with open(metadata_path, "w") as f:
                json.dump(video_data, f, indent=2)
        except Exception:
            pass
    
    def extract_audio(self, video_path: str, audio_path: str):
        """Extract audio from video file using FFmpeg."""
        try:
            cmd = [
                settings.FFMPEG_BIN, "-i", video_path,
                "-ab", "160k", "-ac", "2", "-ar", "44100",
                "-vn", audio_path, "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except FileNotFoundError:
            print("FFmpeg not found. Set FFMPEG_BIN in .env to the full path of ffmpeg.exe (e.g., C:\\ffmpeg\\bin\\ffmpeg.exe) or add it to PATH.")
            return False
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            print(f"Error extracting audio: {stderr}")
            return False
    
    def transcribe_audio(self, audio_path: str):
        """Transcribe audio using Whisper."""
        try:
            if self.whisper_model is None:
                raise RuntimeError("Whisper model not available. Check installation of openai-whisper and torch.")
            # Ensure ffmpeg is on PATH for Whisper's internal calls
            try:
                ffbin = settings.FFMPEG_BIN
                if os.path.isabs(ffbin):
                    ffdir = os.path.dirname(ffbin)
                    current_path = os.environ.get("PATH", "")
                    if ffdir and ffdir not in current_path:
                        os.environ["PATH"] = ffdir + os.pathsep + current_path
            except Exception:
                pass
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )
            return result
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def _hash_file(self, file_path: str) -> str:
        """Compute SHA256 of a file for caching purposes."""
        sha = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha.update(chunk)
        return sha.hexdigest()
    
    def create_caption_clips(self, transcription: dict, caption_style: CaptionStyle, video_duration: float):
        """Create caption clips from transcription using Pillow (no ImageMagick)."""
        caption_clips = []

        # Helper: resolve a PIL font from a name or path
        def resolve_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
            # If a valid path provided
            try:
                if name and (name.lower().endswith('.ttf') or name.lower().endswith('.otf')) and os.path.exists(name):
                    return ImageFont.truetype(name, size)
            except Exception:
                pass
            # Try by name directly (Pillow may find on Windows fonts dir)
            try:
                return ImageFont.truetype(name if name else 'arial.ttf', size)
            except Exception:
                # Try common Windows fonts
                for candidate in ['C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/calibri.ttf', 'C:/Windows/Fonts/tahoma.ttf', 'C:/Windows/Fonts/verdana.ttf', 'C:/Windows/Fonts/times.ttf']:
                    try:
                        if os.path.exists(candidate):
                            return ImageFont.truetype(candidate, size)
                    except Exception:
                        continue
            # Fallback to default bitmap font
            return ImageFont.load_default()

        font = resolve_font(caption_style.font_type, caption_style.font_size)

        for segment in transcription.get("segments", []):
            text = (segment.get("text") or "").strip()
            start_time = float(segment.get("start", 0))
            end_time = min(float(segment.get("end", 0)), video_duration)

            if not text or end_time <= start_time:
                continue

            # Render text to transparent RGBA image using PIL
            # Create a dummy image to measure text bbox with stroke
            dummy_img = Image.new('RGBA', (10, 10), (0, 0, 0, 0))
            draw = ImageDraw.Draw(dummy_img)
            bbox = draw.textbbox((0, 0), text, font=font, stroke_width=caption_style.stroke_width)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            pad = caption_style.padding
            img_w = text_w + pad * 2
            img_h = text_h + pad * 2

            img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Draw text with stroke for readability
            draw.text(
                (pad, pad),
                text,
                font=font,
                fill=caption_style.font_color,
                stroke_width=caption_style.stroke_width,
                stroke_fill=caption_style.stroke_color
            )

            np_img = np.array(img)
            clip = ImageClip(np_img).set_start(start_time).set_end(end_time)
            # Position: center horizontally, bottom with padding from bottom edge handled in overlay by explicit y
            caption_clips.append(clip)

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
                # Place each clip at bottom with padding using video height
                placed = []
                for c in caption_clips:
                    h = video.h
                    y = max(0, h - caption_style.padding - int(c.h))
                    placed.append(c.set_position(('center', y)))
                final_video = CompositeVideoClip([video] + placed)
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
    
    async def process_video(self, video_id: str, video_path: str, caption_style: CaptionStyle, simulate: bool = False):
        """Process video with captions.

        If simulate=True (or global setting enabled via config), heavy media work is skipped
        and steps are advanced over a fixed total duration so the UI can demonstrate progress.
        """
        
        try:
            # Update status to processing
            self.update_video_status(video_id, "processing")
            # Ensure queued/download steps are marked done; activate extract explicitly
            try:
                metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        video_data = json.load(f)
                    steps = video_data.get("steps", [])
                    now = datetime.now(timezone.utc).isoformat()
                    for s in steps:
                        if s.get("key") in ("queued", "download") and s.get("status") in ("active", "queued"):
                            s["status"] = "done"
                            if not s.get("at"):
                                s["at"] = now
                    # If no current active step, set extract active preemptively
                    has_active = any(s.get("status") == "active" for s in steps)
                    if not has_active:
                        for s in steps:
                            if s.get("key") == "extract":
                                s["status"] = "active"
                                s["at"] = now
                                break
                    video_data["steps"] = steps
                    with open(metadata_path, "w") as f:
                        json.dump(video_data, f, indent=2)
            except Exception:
                pass
            # Also call update helper to guarantee extract marked active
            self._update_step(video_id, "extract", "active")
            
            # EARLY EXIT: simulation mode
            if simulate or settings.SIMULATE_PROCESSING:
                # Determine sequence of remaining steps (excluding already done ones)
                step_keys = ["extract", "transcribe", "overlay", "finalize"]
                metadata_path = Path(settings.STORAGE_PATH) / f"{video_id}.json"
                total = settings.SIMULATED_TOTAL_SECONDS
                per_step = max(1, total // len(step_keys))
                for idx, key in enumerate(step_keys):
                    # mark active
                    self._update_step(video_id, key, "active")
                    await asyncio.sleep(per_step)
                    # mark done
                    self._update_step(video_id, key, "done")
                # finalize status
                # Create a simulated captioned output so downloads succeed
                try:
                    output_video = os.path.join(settings.STORAGE_PATH, f"{video_id}_captioned.mp4")
                    if not os.path.exists(output_video):
                        if os.path.isfile(video_path):
                            shutil.copyfile(video_path, output_video)
                            print(f"[simulate] Copied original to {output_video}")
                        else:
                            with open(output_video, 'wb') as f:
                                f.write(b'')
                            print(f"[simulate] Created placeholder file {output_video}")
                except Exception as _e:
                    print(f"Simulation output creation failed for {video_id}: {_e}")
                self.update_video_status(video_id, "completed")
                self._update_step(video_id, "finalize", "done")
                return

            # Create temporary files
            temp_audio = os.path.join(settings.TEMP_PATH, f"{video_id}.wav")
            output_video = os.path.join(settings.STORAGE_PATH, f"{video_id}_captioned.mp4")
            
            # Extract audio
            if not self.extract_audio(video_path, temp_audio):
                raise Exception("Failed to extract audio from video. Check FFmpeg installation.")
            self._update_step(video_id, "extract", "done")
            self._update_step(video_id, "transcribe", "active")
            
            # Transcribe audio with caching
            Path(settings.TRANSCRIPT_CACHE_PATH).mkdir(parents=True, exist_ok=True)
            audio_hash = self._hash_file(temp_audio)
            cache_file = os.path.join(settings.TRANSCRIPT_CACHE_PATH, f"{audio_hash}.json")

            if os.path.exists(cache_file):
                with open(cache_file, 'r') as cf:
                    transcription = json.load(cf)
            else:
                transcription = self.transcribe_audio(temp_audio)
                if transcription:
                    with open(cache_file, 'w') as cf:
                        json.dump(transcription, cf)
            if not transcription:
                raise Exception("Failed to transcribe audio")
            self._update_step(video_id, "transcribe", "done")
            self._update_step(video_id, "overlay", "active")
            
            # Save transcription
            transcript_path = os.path.join(settings.STORAGE_PATH, f"{video_id}_transcript.json")
            with open(transcript_path, "w") as f:
                json.dump(transcription, f, indent=2)
            
            # Overlay captions
            if not self.overlay_captions(video_path, output_video, transcription, caption_style):
                raise Exception("Failed to overlay captions")
            self._update_step(video_id, "overlay", "done")
            self._update_step(video_id, "finalize", "active")
            
            # Update status to completed
            self.update_video_status(video_id, "completed")
            self._update_step(video_id, "finalize", "done")
            
            # Clean up temporary files
            if os.path.exists(temp_audio):
                os.unlink(temp_audio)
            
        except Exception as e:
            print(f"Error processing video {video_id}: {e}")
            self.update_video_status(video_id, "failed", str(e))
            self._update_step(video_id, "finalize", "error")
            
            # Clean up on error
            temp_audio = os.path.join(settings.TEMP_PATH, f"{video_id}.wav")
            if os.path.exists(temp_audio):
                os.unlink(temp_audio)