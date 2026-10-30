"""Encode Recording/frames/f_*.png into an H.264 MP4 with Blender's sequencer (no system ffmpeg needed).

  blender --background --factory-startup --python Tools/encode_frames.py -- <frames_dir> <out.mp4> [fps]
"""
import bpy, sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
frames = sorted(Path(args[0]).glob('f_*.png'))
out = Path(args[1]); fps = int(args[2]) if len(args) > 2 else 30
assert frames, 'no frames'

s = bpy.context.scene
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1280, 720, 100
s.render.fps = fps
se = s.sequence_editor_create()
strip = se.strips.new_image('frames', str(frames[0]), channel=1, frame_start=1)
for f in frames[1:]:
    strip.elements.append(f.name)
s.frame_start, s.frame_end = 1, len(frames)
if hasattr(s.render.image_settings, 'media_type'): s.render.image_settings.media_type = 'VIDEO'   # Blender 5.x
s.render.image_settings.file_format = 'FFMPEG'
s.render.ffmpeg.format = 'MPEG4'
s.render.ffmpeg.codec = 'H264'
s.render.ffmpeg.constant_rate_factor = 'HIGH'
s.render.ffmpeg.ffmpeg_preset = 'GOOD'
s.render.ffmpeg.audio_codec = 'NONE'
s.render.filepath = str(out)
s.render.use_file_extension = False
bpy.ops.render.render(animation=True)
print('ENCODED', out, len(frames), 'frames')
