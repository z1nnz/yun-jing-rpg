using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // joshsu54's old-channel waterworks (PR #52, art/exports/qingxi-waterworks-b) in the novice village, laid out
    // from his R1 plan (tools/qingxi-waterworks-b/village/r1_village_layout.json): the creek intake south of the
    // creek bend down to the field cistern. Before the repair only the old base and the worn trough are there; once
    // the newcomer picks a way to bring the water back (waterworks-commit), the new troughs, gate, wheel, patch,
    // spillway, water and the completion stele appear. FBX and textures are copied into a gitignored folder.
    public static class QingxiWaterworksB
    {
        public const string Models = "Assets/YunJing/Models/WaterworksB";   // copied from art/exports, gitignored

        [Serializable] class Piece { public string id, label, name; public float x, z, yaw, base_y; }
        [Serializable] class Layout { public Piece[] pieces; }

        // Already there before the repair: the old square base and the worn stepped-wall trough (board.json "old").
        static readonly string[] Old = { "B01", "B02-V02" };

        public static void Copy()
        {
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            string src = Path.Combine(repo, "art/exports/qingxi-waterworks-b"), dst = Path.Combine(repo, "apps/game", Models);
            foreach (var dir in Directory.GetDirectories(src))
            {
                var id = Path.GetFileName(dir);
                if (!id.StartsWith("B")) continue;
                var to = Path.Combine(dst, id); Directory.CreateDirectory(to);
                foreach (var file in Directory.GetFiles(dir, "*.fbx").Concat(Directory.Exists(Path.Combine(dir, id + ".fbm")) ? Directory.GetFiles(Path.Combine(dir, id + ".fbm")) : new string[0]))
                {
                    if (new FileInfo(file).Length < 1024 && file.EndsWith(".fbx")) throw new InvalidOperationException("Git LFS pointer instead of asset; run git lfs pull: " + file);
                    var sub = Path.GetFileName(Path.GetDirectoryName(file)).EndsWith(".fbm") ? Path.Combine(to, id + ".fbm") : to;
                    Directory.CreateDirectory(sub);
                    var target = Path.Combine(sub, Path.GetFileName(file));
                    if (!File.Exists(target) || new FileInfo(target).Length != new FileInfo(file).Length) File.Copy(file, target, true);
                }
            }
            // joshsu54's own texture set (his Unity test project), shared by every piece.
            var texSrc = Path.Combine(repo, "tools/qingxi-waterworks-b/unity/Assets/QingxiWaterworksB/Textures");
            var texDst = Path.Combine(dst, "textures"); Directory.CreateDirectory(texDst);
            foreach (var file in Directory.GetFiles(texSrc, "*.png"))
            {
                var target = Path.Combine(texDst, Path.GetFileName(file));
                if (!File.Exists(target) || new FileInfo(target).Length != new FileInfo(file).Length) File.Copy(file, target, true);
            }
            AssetDatabase.Refresh();
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Models + "/textures" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                bool normal = path.EndsWith("_n.png");
                var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                if (ti.textureType == type && ti.maxTextureSize == 2048) continue;
                ti.textureType = type; ti.sRGBTexture = !normal; ti.maxTextureSize = 2048; ti.SaveAndReimport();
            }
            Directory.CreateDirectory(Path.Combine(repo, "apps/game", MaterialFolder));
            var materials = Directory.GetFiles(Path.Combine(repo, "tools/qingxi-waterworks-b/unity/Assets/QingxiWaterworksB/Materials"), "ww_*.mat")
                .Select(f => (name: Path.GetFileNameWithoutExtension(f), mat: Material(Path.GetFileNameWithoutExtension(f), File.ReadAllText(f)))).ToArray();
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Models }))
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(guid));
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
                foreach (var (name, mat) in materials) importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(UnityEngine.Material), name), mat);
                importer.SaveAndReimport();
            }
        }

        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/WaterworksB";

        // URP twin of one of joshsu54's materials: same texture (ww_<name>.png, normal ww_<name>_n.png; the stone
        // family shares ww_stone_n), colour, gloss and metal as his .mat; the water ones transparent.
        static Material Material(string name, string yaml)
        {
            float Number(string key, float fallback)
            {
                var m = System.Text.RegularExpressions.Regex.Match(yaml, $@"- {key}: ([-0-9.eE]+)");
                return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : fallback;
            }
            var c = System.Text.RegularExpressions.Regex.Match(yaml, @"- _Color: \{r: ([0-9.]+), g: ([0-9.]+), b: ([0-9.]+), a: ([0-9.]+)\}");
            var colour = c.Success ? new Color(float.Parse(c.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture), float.Parse(c.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture),
                float.Parse(c.Groups[3].Value, System.Globalization.CultureInfo.InvariantCulture), float.Parse(c.Groups[4].Value, System.Globalization.CultureInfo.InvariantCulture)) : Color.white;
            var path = $"{MaterialFolder}/{name}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            var baseMap = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/textures/{name}.png");
            if (baseMap != null) mat.SetTexture("_BaseMap", baseMap);
            var normal = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/textures/{name}_n.png")
                ?? (name.StartsWith("ww_stone") ? AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/textures/ww_stone_n.png") : null);
            if (normal != null) { mat.SetTexture("_BumpMap", normal); mat.EnableKeyword("_NORMALMAP"); }
            mat.SetColor("_BaseColor", colour);
            mat.SetFloat("_Smoothness", Number("_Glossiness", .2f)); mat.SetFloat("_Metallic", Number("_Metallic", 0));
            if (name.StartsWith("ww_water"))
            {
                mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);
                mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
                mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0); mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static GameObject Spawn(string file, Transform parent, Piece p)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"{Models}/{p.id}/{file}.fbx");
            if (source == null) return null;
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = $"{p.label} {p.name} - by joshsu54";
            model.transform.SetParent(parent, false);
            model.transform.localRotation = Quaternion.Euler(0, p.yaw, 0) * source.transform.localRotation;
            model.transform.localPosition = new Vector3(p.x, p.base_y, p.z);
            return model;
        }

        public static QingxiWaterworksSite Build(Transform village)
        {
            Copy();
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(Path.Combine(repo, "tools/qingxi-waterworks-b/village/r1_village_layout.json")));
            var site = new GameObject("OldChannel (PR #52, R1 layout)").AddComponent<QingxiWaterworksSite>();
            site.transform.SetParent(village, false);
            var repaired = new GameObject("After repair").transform; repaired.SetParent(site.transform, false);
            int placed = 0;
            foreach (var p in layout.pieces)
            {
                // The old pieces stand from the start and stay; everything else appears with the repair.
                if (Spawn(p.id, Old.Contains(p.id) ? site.transform : repaired, p) != null) placed++;
                // Water runs through every channel piece only once the channel is repaired.
                var water = Spawn(p.id + "_water", repaired, p);
                if (water != null) foreach (var r in water.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            site.repaired = repaired.gameObject;
            // The interaction point beside the gate (B05), as joshsu54's layout notes suggest.
            var gate = layout.pieces.FirstOrDefault(p => p.id == "B05");
            var point = new GameObject("Waterworks talk point").transform; point.SetParent(site.transform, false);
            point.localPosition = gate != null ? new Vector3(gate.x - 1.2f, gate.base_y, gate.z) : new Vector3(-31, .3f, -15);
            site.point = point;
            Debug.Log($"QINGXI_WATERWORKS: {placed} channel pieces from the R1 layout");
            return site;
        }
    }
}
