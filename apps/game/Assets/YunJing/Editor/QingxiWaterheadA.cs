using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Johnnnny0823's upstream investigation kit (PR #45, art/exports/qingxi-waterhead-a) in the D3 upstream valley.
    // Each piece ships LOD0/1/2 meshes, a water node, a foliage node, sometimes a convex _Collision shell, and the
    // river tiles carry SOCKET_downstream / SOCKET_upstream empties, so the brook is chained socket to socket.
    // FBX and textures are copied into a gitignored model folder (as the gathering kit is); materials are built here.
    public static class QingxiWaterheadA
    {
        public const string Models = "Assets/YunJing/Models/WaterheadA";   // copied from art/exports, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/WaterheadA";
        const float BankTop = 1.15f;    // river_interface.bank_top_m: banks meet the ground with the origin this far down

        public static string ModelPath(string key) => $"{Models}/{key}.fbx";

        /// <summary>The silt bar and its cleared state from the last RiverKit, handed to the clue spots.</summary>
        public static GameObject SiltBlocked, SiltCleared;

        public static void Copy()
        {
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            string src = Path.Combine(repo, "art/exports/qingxi-waterhead-a"), dst = Path.Combine(repo, "apps/game", Models);
            foreach (var (from, to, pattern) in new[] { (src, dst, "*.fbx"), (Path.Combine(src, "textures"), Path.Combine(dst, "textures"), "*.png") })
            {
                Directory.CreateDirectory(to);
                foreach (var file in Directory.GetFiles(from, pattern))
                {
                    if (new FileInfo(file).Length < 1024) throw new InvalidOperationException("Git LFS pointer instead of asset; run git lfs pull: " + file);
                    var target = Path.Combine(to, Path.GetFileName(file));
                    if (!File.Exists(target) || new FileInfo(target).Length != new FileInfo(file).Length) File.Copy(file, target, true);
                }
            }
            AssetDatabase.Refresh();
            Directory.CreateDirectory(Path.Combine(repo, "apps/game", MaterialFolder));
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Models }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                bool normal = path.EndsWith("_Normal.png"), linear = normal || path.EndsWith("_ORM.png");
                var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                if (ti.textureType == type && ti.sRGBTexture == !linear && ti.maxTextureSize == 2048) continue;
                ti.textureType = type; ti.sRGBTexture = !linear; ti.maxTextureSize = 2048; ti.SaveAndReimport();
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Models }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var key = Path.GetFileNameWithoutExtension(path);
                var importer = (ModelImporter)AssetImporter.GetAtPath(path);
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
                // The three material names each piece uses (model_info validation.materials).
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_" + key), PieceMaterial(key));
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "GrassClump"), GrassMaterial());
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "LowWater"), WaterMaterial());
                importer.SaveAndReimport();
            }
        }

        static Material Mat(string name, string shader = "Universal Render Pipeline/Lit")
        {
            var path = $"{MaterialFolder}/{name}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find(shader)); AssetDatabase.CreateAsset(mat, path); }
            return mat;
        }

        static Material PieceMaterial(string key)
        {
            var mat = Mat(key);
            string tex = $"{Models}/textures/T_{key}_";
            var baseColor = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "BaseColor.png");
            if (baseColor == null) throw new FileNotFoundException("Upstream kit texture missing", tex + "BaseColor.png");
            mat.SetTexture("_BaseMap", baseColor); mat.SetColor("_BaseColor", Color.white); mat.SetFloat("_Smoothness", .22f);
            var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "Normal.png");
            if (normal != null) { mat.SetTexture("_BumpMap", normal); mat.EnableKeyword("_NORMALMAP"); }
            // A12 water-vein resonance stone: the faint glow of its veins.
            var emission = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "Emissive.png");
            if (emission != null) { mat.SetTexture("_EmissionMap", emission); mat.SetColor("_EmissionColor", Color.white * .8f); mat.EnableKeyword("_EMISSION"); }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Dry sedge and grass tufts on the banks: one tone, both faces (the blades are single planes).
        static Material GrassMaterial()
        {
            var mat = Mat("GrassClump");
            mat.SetColor("_BaseColor", new Color(.56f, .52f, .33f)); mat.SetFloat("_Smoothness", .1f);
            mat.SetFloat("_Cull", 0);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // The low water left in the cut-off channel: thin, clear, a little green, with the shared ripple normal.
        static Material WaterMaterial()
        {
            var mat = Mat("LowWater");
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);
            mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            mat.SetColor("_BaseColor", new Color(.30f, .44f, .40f, .55f)); mat.SetFloat("_Smoothness", .88f);
            var ripple = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Models}/textures/T_WW_Water_Normal.png");
            if (ripple != null) { mat.SetTexture("_BumpMap", ripple); mat.SetFloat("_BumpScale", .35f); mat.EnableKeyword("_NORMALMAP"); }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        public static bool Owns(string modelPath) => modelPath != null && modelPath.StartsWith(Models + "/");

        // LOD group (land LOD0/1/2; water on every level, foliage only up close), and collision: the convex
        // _Collision shell when the piece has one, otherwise a mesh collider on LOD1 for the walkable river tiles.
        public static void Prepare(GameObject model, bool walkable)
        {
            var all = model.GetComponentsInChildren<Transform>(true);
            Renderer Find(string suffix) => all.FirstOrDefault(t => t.name.EndsWith(suffix))?.GetComponent<Renderer>();
            var shell = all.FirstOrDefault(t => t.name.EndsWith("_Collision"));
            if (shell != null)
            {
                var r = shell.GetComponent<Renderer>(); if (r != null) UnityEngine.Object.DestroyImmediate(r);
                var mf = shell.GetComponent<MeshFilter>();
                if (mf != null) { var mc = shell.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; mc.convex = true; }
            }
            Renderer lod0 = Find("_LOD0"), lod1 = Find("_LOD1"), lod2 = Find("_LOD2"), water = Find("_Water"), foliage = Find("_Foliage");
            if (lod0 != null && lod1 != null && lod2 != null)
            {
                Renderer[] Level(params Renderer[] rs) => rs.Where(r => r != null).ToArray();
                // Unity already makes a LOD group for *_LOD0/1/2 meshes; set its levels so water and grass are in it.
                var group = model.GetComponent<LODGroup>() ?? model.AddComponent<LODGroup>();
                group.SetLODs(new[]
                {
                    new LOD(.35f, Level(lod0, water, foliage)),
                    new LOD(.12f, Level(lod1, water)),
                    new LOD(.015f, Level(lod2, water)),
                });
                group.RecalculateBounds();
            }
            if (walkable && shell == null && (lod1 ?? lod0) != null)
            {
                var mc = (lod1 ?? lod0).gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = (lod1 ?? lod0).GetComponent<MeshFilter>().sharedMesh;
            }
            foreach (var r in model.GetComponentsInChildren<Renderer>())
                if (r.name.EndsWith("_Water") || r.name.EndsWith("_Foliage")) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        static GameObject Spawn(string key, Transform parent)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath(key));
            if (source == null) throw new FileNotFoundException("Upstream kit model missing", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = key + " - by Johnnnny0823";
            model.transform.SetParent(parent, false);
            return model;
        }

        // ------------------------------------------------------------------ the brook
        // The D3 creek line (blocks/D3.json) is walked from its south-east end; at each step the next tile's
        // downstream socket goes where the last tile's upstream socket ended, turned to face the line a tile
        // ahead, and dropped so its banks meet the ground. creekKit names the tiles for each stretch.
        public static int RiverKit(Transform parent, QingxiVillageTerrain.Layout layout)
        {
            var c = layout.creek;
            if (layout.creekKit == null || layout.creekKit.Length == 0 || c == null || c.Count < 2) return 0;
            var root = new GameObject("UpstreamBrook (creekKit, PR #45)").transform; root.SetParent(parent, false);
            var line = new List<Vector2>(); for (int i = 0; i < c.Count; i++) line.Add(c[i]);
            float total = 0; for (int i = 1; i < line.Count; i++) total += Vector2.Distance(line[i - 1], line[i]);
            float along = 0; var at = line[0]; int placed = 0, step = 0;
            while (along < total - 2f)
            {
                var span = layout.creekKit.FirstOrDefault(s => along >= s.from && along < s.to) ?? layout.creekKit.Last();
                var keys = span.pieces.Split(',', '/').Select(k => k.Trim()).Where(k => k.StartsWith("A01_")).ToArray();
                bool last = along > total - 8f;
                string key = last ? "A01_end_source_01" : keys.Length > 0 ? keys[step % keys.Length] : "A01_straight_01";
                var ahead = PointAt(line, Mathf.Min(along + 6f, total));
                var dir = (ahead - at).normalized;
                var tile = Spawn(key, root);
                var down = Socket(tile, "SOCKET_downstream"); var up = Socket(tile, "SOCKET_upstream");
                if (down == null) throw new InvalidDataException(key + " has no SOCKET_downstream");
                // The source end is terminal (no upstream socket): its body lies upstream of the downstream socket.
                var axis = up != null ? up.position - down.position : Centre(tile) - down.position;
                tile.transform.rotation = Quaternion.FromToRotation(Flat(axis), new Vector3(dir.x, 0, dir.y)) * tile.transform.rotation;
                float ground = QingxiVillageTerrain.BaseHeight(layout, at.x, at.y);
                tile.transform.position += new Vector3(at.x, ground - BankTop + .03f, at.y) - down.position;
                // Pitch the tile up the valley so its upstream end also meets the land (the brook climbs ~12 m).
                var tip = up != null ? up.position : Centre(tile) * 2 - down.position;
                float run = Vector2.Distance(at, new Vector2(tip.x, tip.z));
                float rise = QingxiVillageTerrain.BaseHeight(layout, tip.x, tip.z) - ground;
                var right = Vector3.Cross(Vector3.up, new Vector3(dir.x, 0, dir.y));
                tile.transform.RotateAround(down.position, right, -Mathf.Atan2(rise, run) * Mathf.Rad2Deg);
                Prepare(tile, walkable: true);
                placed++;
                if (up == null) break;
                var next = new Vector2(up.position.x, up.position.z);
                along += Vector2.Distance(at, next); at = next; step++;
                if (last) break;
            }
            Dress(root, layout, line, total);
            Debug.Log($"QINGXI_UPSTREAM_BROOK: {placed} tiles over {total:F0} m of creek");
            return placed;
        }

        // In-channel pieces: the silt bar where the creek narrows (the silt_buildup clue), the stepping slabs at the
        // crossing to the nursery bank, and withered sedge along the middle stretch.
        static void Dress(Transform root, QingxiVillageTerrain.Layout layout, List<Vector2> line, float total)
        {
            GameObject Put(string key, Vector2 p, float yaw, float lift = 0)
            {
                var m = Spawn(key, root);
                m.transform.rotation = Quaternion.Euler(0, yaw, 0) * m.transform.rotation;
                float land = QingxiVillageTerrain.BaseHeight(layout, p.x, p.y);
                m.transform.position = new Vector3(p.x, land - BankTop + .25f + lift, p.y);
                Prepare(m, walkable: true);
                return m;
            }
            float Heading(float d) { var a = PointAt(line, d); var b = PointAt(line, Mathf.Min(d + 2, total)); return Mathf.Atan2(b.x - a.x, b.y - a.y) * Mathf.Rad2Deg; }
            SiltBlocked = Put("A04_SiltBar", SiltPoint(layout), Heading(42));
            SiltCleared = Put("A04_SiltBar_cleared", SiltPoint(layout), Heading(42));
            SiltCleared.SetActive(false);
            Put("A04_SiltJam_03", PointAt(line, 48), Heading(48));
            var crossing = layout.creek.crossing != null ? new Vector2(layout.creek.crossing.x, layout.creek.crossing.z) : PointAt(line, 62);
            Put("A08_slabs_stagger_01", crossing, Heading(62) + 90);
            var random = new System.Random(45);
            for (float d = 68; d < Mathf.Min(104, total); d += 7)
            {
                var p = PointAt(line, d); var q = PointAt(line, d + 1); var side = new Vector2(q.y - p.y, p.x - q.x).normalized;
                var bank = p + side * ((random.Next(2) == 0 ? 1 : -1) * 2.9f);
                var m = Spawn("A05_WitheredSedge_0" + (1 + random.Next(3)), root);
                m.transform.rotation = Quaternion.Euler(0, random.Next(360), 0) * m.transform.rotation;
                QingxiVillageTerrain.CreekDistance(layout, bank.x, bank.y, out float shelf);   // the flat shelf under the tiles
                m.transform.position = new Vector3(bank.x, shelf + .03f, bank.y);
                Prepare(m, walkable: false);
            }
        }

        /// <summary>Where the silt bar sits (42 m up the creek): the silt_buildup clue is read here.</summary>
        public static Vector2 SiltPoint(QingxiVillageTerrain.Layout layout)
        {
            var c = layout.creek; var line = new List<Vector2>(); for (int i = 0; i < c.Count; i++) line.Add(c[i]);
            return PointAt(line, 42);
        }

        static Vector3 Centre(GameObject model)
        {
            var rs = model.GetComponentsInChildren<Renderer>(); var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b.center;
        }

        static Transform Socket(GameObject tile, string name) => tile.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name);
        static Vector3 Flat(Vector3 v) { v.y = 0; return v.sqrMagnitude < 1e-6f ? Vector3.forward : v.normalized; }

        static Vector2 PointAt(List<Vector2> line, float distance)
        {
            for (int i = 1; i < line.Count; i++)
            {
                float seg = Vector2.Distance(line[i - 1], line[i]);
                if (distance <= seg) return Vector2.Lerp(line[i - 1], line[i], distance / Mathf.Max(seg, 1e-4f));
                distance -= seg;
            }
            return line[line.Count - 1];
        }
    }
}
