from yt_dlp import YoutubeDL
from pathlib import Path

# choose where to save
output_dir = Path("~/uofthacks/test/videos").expanduser()
output_dir.mkdir(exist_ok=True)

url = "https://www.youtube.com/shorts/YUa0tV9OuKg"

ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
    "ffmpeg_location": r"C:\Users\janwa\ffmpeg\bin",  # <-- Add this line, adjust if your path differs
}
with YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])