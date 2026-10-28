// Copies the waterworks kit (FBX, textures, model_info.json) from art/exports/qingxi-waterworks-b into
// Assets/Resources/Kit (git-ignored). The exports stay the only source of truth; re-run after a rebuild of the kit.
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Qingxi.Waterworks.EditorTools
{
    public static class KitSync
    {
        public static string ExportDir => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "..", "art", "exports", "qingxi-waterworks-b"));
        public const string KitDir = "Assets/Resources/Kit";

        [MenuItem("Waterworks/Sync Kit")]
        public static void Sync()
        {
            if (!Directory.Exists(ExportDir)) throw new DirectoryNotFoundException(ExportDir);
            int copied = 0;
            foreach (var dir in Directory.GetDirectories(ExportDir))
            {
                var key = Path.GetFileName(dir);
                var files = Directory.GetFiles(dir, "*", SearchOption.AllDirectories)
                    .Where(f => key == "_shared" || f.EndsWith(".fbx") || f.EndsWith("_model_info.json") || f.Contains(Path.DirectorySeparatorChar + "textures" + Path.DirectorySeparatorChar));
                foreach (var f in files)
                {
                    var rel = f.Substring(dir.Length + 1); var dst = Path.Combine(KitDir, key, rel);
                    Directory.CreateDirectory(Path.GetDirectoryName(dst));
                    var src = new FileInfo(f); var old = new FileInfo(dst);
                    if (old.Exists && old.Length == src.Length && old.LastWriteTimeUtc >= src.LastWriteTimeUtc) continue;
                    File.Copy(f, dst, true); copied++;
                }
            }
            AssetDatabase.Refresh();
            Debug.Log($"[Waterworks] kit sync: {copied} file(s) copied from {ExportDir}");
        }
    }

    /// <summary>Import settings for the kit: metres, blend shapes on (water ripple / gate water), animation off (the scene drives it).</summary>
    public sealed class KitImport : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if (!assetPath.Replace('\\', '/').Contains("/Resources/Kit/")) return;
            var m = (ModelImporter)assetImporter;
            m.globalScale = 1; m.useFileScale = true; m.importBlendShapes = true; m.importAnimation = false;
            m.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription; m.materialLocation = ModelImporterMaterialLocation.InPrefab;
            m.isReadable = false; m.importCameras = false; m.importLights = false;
        }
    }
}
