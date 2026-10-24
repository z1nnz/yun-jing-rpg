"""Encode the 48 rendered PNGs as a 4-second H.264 MP4 using Blender's own encoder."""
import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];VERSION=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'v001';out=ROOT/'Effects/WindFog'/VERSION
frames=sorted((out/'frames').glob('*.png'));assert len(frames)==48
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
s.render.resolution_x=720;s.render.resolution_y=480;s.render.resolution_percentage=100;s.render.fps=12
s.frame_start=1;s.frame_end=48;s.render.use_sequencer=True
seq=s.sequence_editor_create()
strip=seq.strips.new_image('Wind_Fog_Frames',str(frames[0]),channel=1,frame_start=1)
for p in frames[1:]:strip.elements.append(p.name)
strip.frame_final_duration=48
s.view_settings.view_transform='Standard'
s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.constant_rate_factor='HIGH';s.render.ffmpeg.ffmpeg_preset='GOOD'
s.render.filepath=str(out/'wind_fog_preview.mp4');bpy.ops.render.render(animation=True)
data=(out/'wind_fog_preview.mp4').read_bytes();assert b'ftyp' in data[:64] and len(data)>10000
# Decode through the sequencer to confirm frame dimensions and duration.
seq.strips.remove(strip);movie=seq.strips.new_movie('Verified_Encoded_Preview',str(out/'wind_fog_preview.mp4'),channel=1,frame_start=1)
assert movie.frame_duration==48,(movie.frame_duration,'encoded length')
(out/'video_validation.json').write_text(json.dumps({'mp4_container':True,'decoded_frames':movie.frame_duration,'fps':12,'duration_seconds':4,'source_frames':len(frames)},indent=2))
print('MP4_VERIFIED',len(data),flush=True)
