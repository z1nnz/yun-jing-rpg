using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace YunJing.Editor
{
    // Render the generated scene itself so an old Blender blockout cannot be
    // mistaken for the current Unity asset placement.
    public static class QingxiPreviewCapture
    {
        [MenuItem("Yun Jing/Qingxi/Capture current preview overhead")]
        public static void Capture()
        {
            const string scene = "Assets/YunJing/Generated/QingxiWorldPreview.unity";
            EditorSceneManager.OpenScene(scene);
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
            var inventory = Path.Combine(root, "artifacts/qingxi-model-bounds.txt");
            var lines = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None)
                .Where(r => r.enabled && r.gameObject.activeInHierarchy)
                .Select(r => $"{r.gameObject.name}|{r.bounds.center}|{r.bounds.size}|{r.transform.root.name}")
                .OrderBy(s => s);
            Directory.CreateDirectory(Path.GetDirectoryName(inventory));
            File.WriteAllLines(inventory, lines);
            if (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null)
                throw new InvalidOperationException("Overhead capture needs a graphics device; run without -nographics.");
            var go = new GameObject("Temporary Qingxi overhead camera");
            var camera = go.AddComponent<Camera>();
            var texture = new Texture2D(1920, 1280, TextureFormat.RGB24, false);
            var target = RenderTexture.GetTemporary(1920, 1280, 24, RenderTextureFormat.ARGB32);
            try
            {
                camera.transform.position = new Vector3(0, 165, 0);
                camera.transform.rotation = Quaternion.Euler(90, 0, 0);
                camera.orthographic = true;
                camera.orthographicSize = 77;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(.73f, .80f, .77f);
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                texture.ReadPixels(new Rect(0, 0, 1920, 1280), 0, 0);
                texture.Apply();
                var output = Path.Combine(root, "art/previews/qingxi-terrain-pilot-v1/current-unity-overhead.png");
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllBytes(output, texture.EncodeToPNG());
                Debug.Log("QINGXI_OVERHEAD_CAPTURE: " + output);
            }
            finally
            {
                RenderTexture.active = null;
                camera.targetTexture = null;
                RenderTexture.ReleaseTemporary(target);
                UnityEngine.Object.DestroyImmediate(texture);
                UnityEngine.Object.DestroyImmediate(go);
            }
        }
    }
}
