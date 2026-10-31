"""Encode the frames saved by the player's --lesson-capture hook to H.264 MP4 with Blender's bundled FFmpeg (no extra tools).

  blender -b --python-exit-code 1 --python tools/body-training-lesson/encode_video.py -- <frames folder> <out.mp4>
"""
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
frames, out = Path(args[0]).resolve(), Path(args[1]).resolve()
files = sorted(frames.glob('f*.jpg'))
s = bpy.context.scene
s.sequence_editor_create()
seq = s.sequence_editor
strips = seq.strips if hasattr(seq, 'strips') else seq.sequences   # Blender 5.x renamed sequences -> strips
strip = strips.new_image('play', str(files[0]), channel=1, frame_start=1)
for f in files[1:]:
    strip.elements.append(f.name)
s.render.fps = 30
s.frame_start, s.frame_end = 1, len(files)
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 960, 540, 100
if hasattr(s.render.image_settings, 'media_type'):   # Blender 5.x: pick video output before the container
    s.render.image_settings.media_type = 'VIDEO'
s.render.image_settings.file_format = 'FFMPEG'
s.render.ffmpeg.format = 'MPEG4'
s.render.ffmpeg.codec = 'H264'
s.render.ffmpeg.constant_rate_factor = 'MEDIUM'
s.render.ffmpeg.audio_codec = 'NONE'
s.render.use_sequencer = True
s.render.filepath = str(out)
bpy.ops.render.render(animation=True)
print('ENCODED', out, len(files), 'frames', flush=True)
