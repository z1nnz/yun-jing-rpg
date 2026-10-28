"""Turn the demo's window frames into an mp4 with Blender's own sequencer (no ffmpeg install needed).

    blender -b --factory-startup --python encode_frames.py -- FRAMES_DIR OUT.mp4 [fps]
"""
import bpy, sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
frames_dir, out = Path(args[0]).resolve(), Path(args[1]).resolve(); fps = int(args[2]) if len(args) > 2 else 4
files = sorted(frames_dir.glob('f*.png'))
if not files: raise SystemExit(f'no frames in {frames_dir}')

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.sequence_editor_create()
img = bpy.data.images.load(str(files[0])); w, h = img.size; bpy.data.images.remove(img)
strips = sc.sequence_editor.strips if hasattr(sc.sequence_editor, 'strips') else sc.sequence_editor.sequences
s = strips.new_image('demo', str(files[0]), channel=1, frame_start=1)
for f in files[1:]: s.elements.append(f.name)
sc.frame_start, sc.frame_end = 1, len(files)
r = sc.render; r.fps = fps; r.resolution_x, r.resolution_y = w - w % 2, h - h % 2; r.resolution_percentage = 100
r.image_settings.media_type = 'VIDEO' if hasattr(r.image_settings, 'media_type') else r.image_settings.file_format
if r.image_settings.file_format != 'FFMPEG': r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'MEDIUM'
out.parent.mkdir(parents=True, exist_ok=True); r.filepath = str(out)
bpy.ops.render.render(animation=True)
print('wrote', out, len(files), 'frames')
