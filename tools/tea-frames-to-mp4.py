# Assemble the tea playtest frames into an MP4 with Blender's sequencer (no ffmpeg needed on the machine).
# blender --background --factory-startup --python tools/tea-frames-to-mp4.py -- <frames dir> <out.mp4> [fps]
import os, sys
import bpy

frames_dir, out = sys.argv[-3], sys.argv[-2]
fps = int(sys.argv[-1])
files = sorted(f for f in os.listdir(frames_dir) if f.endswith('.png'))
scene = bpy.context.scene
scene.sequence_editor_create()
seqs = scene.sequence_editor.strips if hasattr(scene.sequence_editor, 'strips') else scene.sequence_editor.sequences
strip = seqs.new_image('frames', os.path.join(frames_dir, files[0]), 1, 1)
for f in files[1:]: strip.elements.append(f)
scene.frame_start, scene.frame_end = 1, len(files)
scene.render.fps = fps
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1280, 720, 100
if hasattr(scene.render.image_settings, 'media_type'): scene.render.image_settings.media_type = 'VIDEO'   # Blender 5.x
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format, scene.render.ffmpeg.codec = 'MPEG4', 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.filepath = out
bpy.ops.render.render(animation=True)
print('TEA_MP4', out, len(files), 'frames at', fps, 'fps')
