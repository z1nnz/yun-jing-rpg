"""Encode the recorded WebM playthrough to H.264 MP4 with Blender's bundled FFmpeg (no extra tools). Same approach as
art/source/qingxi-waterhead-a/encode_video.py (PR #45), at real-time speed because the recording is already under a minute.

  blender -b --python-exit-code 1 --python art/source/territory-backyard-a/encode_video.py
Reads art/previews/territory-backyard-a/demo/walkthrough.webm, writes walkthrough_player_view.mp4 beside it at 960 x 540.
"""
from pathlib import Path

import bpy

DEMO = Path(__file__).resolve().parents[3] / 'art/previews/territory-backyard-a/demo'
src, dst = DEMO / 'walkthrough.webm', DEMO / 'walkthrough_player_view.mp4'
s = bpy.context.scene
s.sequence_editor_create()
seq = s.sequence_editor
strips = seq.strips if hasattr(seq, 'strips') else seq.sequences   # Blender 5.x renamed sequences -> strips
movie = strips.new_movie('play', str(src), channel=1, frame_start=1)
fps = movie.fps if movie.fps else 25
s.render.fps = int(round(fps))
s.frame_start, s.frame_end = 1, movie.frame_final_end - 1
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 960, 540, 100
if hasattr(s.render.image_settings, 'media_type'):   # Blender 5.x: pick video output before the container
    s.render.image_settings.media_type = 'VIDEO'
s.render.image_settings.file_format = 'FFMPEG'
s.render.ffmpeg.format = 'MPEG4'
s.render.ffmpeg.codec = 'H264'
s.render.ffmpeg.constant_rate_factor = 'LOW'
s.render.ffmpeg.audio_codec = 'NONE'
s.render.use_sequencer = True
s.render.filepath = str(dst)
bpy.ops.render.render(animation=True)
print('ENCODED', dst, s.frame_end, 'frames at', s.render.fps, 'fps', flush=True)
