using System;
using System.Collections;
using System.Linq;
using QingxiWorld;
using UnityEngine;

namespace YunJing
{
    // Review shots of the D3 upstream valley (--upstream-shots): streams in A3 and D3, then a separate camera takes
    // a few views along the brook and at the clue spots into <build>/upstream-shots/, and the build quits.
    public sealed class QingxiUpstreamShots : MonoBehaviour
    {
        static readonly (string name, Vector3 eye, Vector3 look)[] Views =
        {
            ("01-entry-from-a3", new Vector3(-64, 0, 52), new Vector3(-80, 0, 72)),
            ("02-brook-low", new Vector3(-58, 0, 60), new Vector3(-72, 0, 80)),
            ("03-silt-narrows", new Vector3(-70, 0, 72), new Vector3(-78, 0, 88)),
            ("04-cracked-sluice", new Vector3(-82, 0, 76), new Vector3(-87, 0, 83)),
            ("05-crossing-nursery", new Vector3(-94, 0, 96), new Vector3(-86, 0, 110)),
            ("06-ruin-and-source", new Vector3(-108, 0, 100), new Vector3(-128, 0, 120)),
            ("07-overview", new Vector3(-40, 0, 40), new Vector3(-95, 0, 100)),
        };

        IEnumerator Start()
        {
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "--upstream-shots") < 0) yield break;
            string dir = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Application.dataPath), "upstream-shots");
            System.IO.Directory.CreateDirectory(dir);
            yield return new WaitForSecondsRealtime(3);
            var walker = QingxiFirstPerson.Current;
            var streamer = QingxiBlockStreamer.Current;
            if (walker == null || streamer == null) { Debug.LogError("QINGXI_UPSTREAM_SHOTS no walker or streamer"); Application.Quit(1); yield break; }
            QingxiDayNight.Current?.SetHour(10);
            var body = walker.GetComponent<CharacterController>();
            body.enabled = false; walker.transform.position = new Vector3(-66, 8, 46); body.enabled = true;
            float until = Time.realtimeSinceStartup + 30;
            while ((!streamer.IsLoaded("A3") || !streamer.IsLoaded("D3")) && Time.realtimeSinceStartup < until) yield return null;
            yield return new WaitForSecondsRealtime(2);
            var cam = new GameObject("UpstreamShotsCamera").AddComponent<Camera>();
            cam.fieldOfView = 62; cam.nearClipPlane = .05f; cam.farClipPlane = 400; cam.depth = 50;
            UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(cam).renderPostProcessing = true;
            foreach (var (name, eye, look) in Views)
            {
                float Ground(Vector3 p) => Physics.RaycastAll(new Vector3(p.x, 80, p.z), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore)
                    .Where(h => !h.collider.isTrigger).Select(h => h.point.y).DefaultIfEmpty(0).Max();
                var e = new Vector3(eye.x, Ground(eye) + (name.Contains("overview") ? 28f : 1.7f), eye.z);
                var l = new Vector3(look.x, Ground(look) + .4f, look.z);
                cam.transform.SetPositionAndRotation(e, Quaternion.LookRotation(l - e));
                yield return new WaitForSecondsRealtime(.8f);
                yield return new WaitForEndOfFrame();
                var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); tex.Apply();
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(dir, name + ".png"), tex.EncodeToPNG());
                Destroy(tex);
            }
            Debug.Log("QINGXI_UPSTREAM_SHOTS saved to " + dir);
            Application.Quit(0);
        }
    }
}
