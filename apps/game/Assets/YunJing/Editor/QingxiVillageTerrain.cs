using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // Continuous ground for the novice village, generated from tools/qingxi-terrain/novice-village.json:
    // gentle relief from height points, flat pads under each collaborator zone, roads that follow the
    // relief with a level cross-section, road/plaza/forest paint and grass kept out of roads and pads.
    // Same approach as QingxiEntranceTerrain (PR #48); kept separate so the two pilots don't edit one file.
    public static class QingxiVillageTerrain
    {
        const string Generated = "Assets/YunJing/Generated";
        const int HeightResolution = 257, PaintResolution = 256;
        const float BaseY = -1f, HeightRange = 24f;   // D3 climbs to 15 m; 16-bit heights keep sub-millimetre steps
        const float RoadBlend = 2.5f, PadBlend = 3f;

        [Serializable] public class Area { public float minX, minZ, sizeX, sizeZ; }
        [Serializable] public class Node { public string id; public float x, z; }
        [Serializable] public class Edge { public string id, from, to, surface; public float width; }
        [Serializable] public class Pad { public string id, surface; public float x, z, halfX, halfZ, height; }
        [Serializable] public class HeightPoint { public float x, z, height; }
        [Serializable] public class Checkpoint { public string name, node; }
        // A slot in the village plan. footprint = width, depth, height (m) along the model's own X/Z before yaw;
        // status: placed / ready (model exists, placed by the builder) / needed (no model yet, shown as a box).
        [Serializable]
        public class Placement
        {
            public string id, role, model, author, collider, block, zone, owner, status, phase, note;
            public float x, z, yaw, scale;
            public float[] footprint;
            public bool Needed => status == "needed" || string.IsNullOrEmpty(model);
        }
        [Serializable] public class Herb { public string id, kind; public float x, z; }
        [Serializable] public class FortuneSpot { public string id, title, passage, reward, condition; public float x, z; }
        [Serializable] public class Crossing { public float x, z; public int stones; }
        [Serializable]
        public class Creek
        {
            public float width = 4, depth = .9f, bank = 3, waterLevel = .6f;
            public float[] points = new float[0];   // x, z pairs from upstream to downstream
            public Crossing crossing;
            public int Count => points.Length / 2;
            public Vector2 this[int i] => new Vector2(points[2 * i], points[2 * i + 1]);
        }
        [Serializable]
        public class Layout
        {
            public int version;
            public Area bounds;
            public float noise;
            public Node[] nodes;
            public Edge[] edges;
            public Pad[] pads;
            public HeightPoint[] heightPoints;
            public Checkpoint[] checkpoints;
            public string[] route;
            public Placement[] placements;
            public Placement[] crossingSlots;   // slots off the pads (bridges over the creek)
            public Herb[] herbs;
            public FortuneSpot[] fortunes;   // 機緣 (K4): hidden finds, never on the map
            public Creek creek;
            public CreekKitSpan[] creekKit;   // D3: which river tiles (PR #45) line each stretch of the creek
        }
        [Serializable] public class CreekKitSpan { public float from, to; public string pieces, note; }

        // Distance to the creek's centre line, and the land height there (the bed follows the land, so the
        // water runs downhill). Returns +infinity when the layout has no creek.
        public static float CreekDistance(Layout layout, float x, float z, out float centreLand)
        {
            centreLand = 0;
            var c = layout.creek;
            if (c == null || c.Count < 2) return float.PositiveInfinity;
            float best = float.PositiveInfinity; var p = new Vector2(x, z);
            for (int i = 0; i + 1 < c.Count; i++)
            {
                Vector2 a = c[i], b = c[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
                var q = a + ab * t;
                float d = Vector2.Distance(p, q);
                if (d < best) { best = d; centreLand = BaseHeight(layout, q.x, q.y); }
            }
            return best;
        }

        /// <summary>Height of the water surface at a point on (or near) the creek centre line.</summary>
        public static float WaterHeight(Layout layout, float x, float z)
        {
            CreekDistance(layout, x, z, out float land);
            return land - layout.creek.depth + layout.creek.waterLevel;
        }

        static readonly string[] LayerNames = { "VillageMeadow", "VillagePackedEarth", "VillagePlazaStone", "VillageForestFloor" };
        static readonly Color[] Colors = {
            new Color(.40f, .50f, .31f), new Color(.56f, .44f, .30f), new Color(.52f, .50f, .45f), new Color(.30f, .33f, .22f)
        };

        // A1 (the novice village) by default; other blocks pass their file under tools/qingxi-terrain/blocks/.
        public static Layout Load(string relative = "tools/qingxi-terrain/novice-village.json")
        {
            var file = Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", relative));
            if (!File.Exists(file)) throw new FileNotFoundException("Novice village layout missing", file);
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(file));
            if (layout == null || layout.version < 1 || layout.version > 2 || layout.bounds == null || layout.nodes == null || layout.edges == null || layout.pads == null)
                throw new InvalidDataException("Novice village layout is invalid");
            var ids = layout.nodes.Select(n => n.id).ToHashSet();
            foreach (var edge in layout.edges)
                if (edge.width <= 0 || !ids.Contains(edge.from) || !ids.Contains(edge.to))
                    throw new InvalidDataException("Invalid village road: " + edge.id);
            return layout;
        }

        static float Smooth(float a, float b, float value)
        {
            float t = Mathf.Clamp01((value - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        // Inverse-distance blend of the pad heights and the extra height points: smooth, no ridges.
        internal static float BaseHeight(Layout layout, float x, float z)
        {
            float sum = 0, weights = 0;
            void Add(float px, float pz, float h)
            {
                float d2 = (x - px) * (x - px) + (z - pz) * (z - pz);
                float w = 1f / Mathf.Max(.25f, d2);
                sum += w * h; weights += w;
            }
            foreach (var p in layout.pads) Add(p.x, p.z, p.height);
            foreach (var p in layout.heightPoints ?? new HeightPoint[0]) Add(p.x, p.z, p.height);
            return weights > 0 ? sum / weights : 0;
        }

        // Signed distance to the road union (negative inside), and the centre-line height nearest to the point.
        public static float RoadDistance(Layout layout, float x, float z, out float centreHeight)
        {
            var nodes = layout.nodes.ToDictionary(n => n.id);
            float best = float.MaxValue; centreHeight = 0;
            foreach (var edge in layout.edges)
            {
                Node a = nodes[edge.from], b = nodes[edge.to];
                var ab = new Vector2(b.x - a.x, b.z - a.z);
                var ap = new Vector2(x - a.x, z - a.z);
                float t = ab.sqrMagnitude < .0001f ? 0 : Mathf.Clamp01(Vector2.Dot(ap, ab) / ab.sqrMagnitude);
                float d = (ap - ab * t).magnitude - edge.width * .5f;
                if (d >= best) continue;
                best = d;
                centreHeight = BaseHeight(layout, a.x + ab.x * t, a.z + ab.y * t);
            }
            return best;
        }

        // Signed distance to the nearest pad (negative inside). Paint uses rounded corners so pads don't read as
        // rectangles; the height platform itself stays rectangular.
        public static float PadDistance(Layout layout, float x, float z, out Pad nearest, float cornerRadius = 0)
        {
            float best = float.MaxValue; nearest = null;
            foreach (var p in layout.pads)
            {
                float r = Mathf.Min(cornerRadius, Mathf.Min(p.halfX, p.halfZ));
                float qx = Mathf.Abs(x - p.x) - (p.halfX - r), qz = Mathf.Abs(z - p.z) - (p.halfZ - r);
                float d = new Vector2(Mathf.Max(qx, 0), Mathf.Max(qz, 0)).magnitude + Mathf.Min(Mathf.Max(qx, qz), 0) - r;
                if (d < best) { best = d; nearest = p; }
            }
            return best;
        }

        // K5: one gentle height field shared by the whole world. Every block blends to it over its outer 12 m, so
        // two neighbouring blocks meet at exactly the same height with no seam or cliff.
        public static float WorldBase(float x, float z) =>
            .7f + 1.1f * (Mathf.PerlinNoise(x * .011f + 3.3f, z * .011f + 8.1f) - .5f);

        public static float Height(Layout layout, float x, float z)
        {
            float h = BaseHeight(layout, x, z)
                + layout.noise * 2f * (Mathf.PerlinNoise(x * .05f + 11f, z * .05f + 7f) - .5f)
                + layout.noise * (Mathf.PerlinNoise(x * .17f + 53f, z * .17f + 29f) - .5f);
            float road = RoadDistance(layout, x, z, out float roadHeight);
            h = Mathf.Lerp(roadHeight, h, Smooth(0f, RoadBlend, road));
            var area = layout.bounds;
            float border = Mathf.Min(Mathf.Min(x - area.minX, area.minX + area.sizeX - x), Mathf.Min(z - area.minZ, area.minZ + area.sizeZ - z));
            h = Mathf.Lerp(WorldBase(x, z), h, Smooth(1f, 12f, border));
            // Creek: a flat bed (depth below the land at the centre line) easing up the banks.
            float creek = CreekDistance(layout, x, z, out float creekLand);
            if (!float.IsPositiveInfinity(creek))
            {
                var c = layout.creek;
                float bed = creekLand - c.depth + .05f * (Mathf.PerlinNoise(x * .4f, z * .4f) - .5f);
                // D3: the river tiles (PR #45) are 7 m wide and level across, so the corridor under them is a flat
                // shelf at the centre-line land (no noise, no side slope) that eases back into the hillside.
                if (layout.creekKit != null && layout.creekKit.Length > 0)
                    h = Mathf.Lerp(creekLand, h, Smooth(c.width * .5f + c.bank + .6f, c.width * .5f + c.bank + 4.6f, creek));
                h = Mathf.Lerp(bed, h, Smooth(c.width * .35f, c.width * .5f + c.bank, creek));
            }
            // Pads last: each zone stands on one flat platform at its stated height.
            foreach (var p in layout.pads)
            {
                float edge = Mathf.Max(Mathf.Abs(x - p.x) - p.halfX, Mathf.Abs(z - p.z) - p.halfZ);
                h = Mathf.Lerp(p.height, h, Smooth(0f, PadBlend, edge));
            }
            return h;
        }

        /// <summary>World-space ground height under (x, z) on the generated terrain.</summary>
        public static float Ground(Terrain terrain, float x, float z) =>
            terrain.SampleHeight(new Vector3(x, 0, z)) + terrain.transform.position.y;

        public static Terrain Create(Transform parent) => Create(parent, Load(), "NoviceVillageTerrain", "NoviceVillageTerrain (route data)");

        public static Terrain Create(Transform parent, Layout layout, string asset, string objectName)
        {
            var area = layout.bounds;
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(Generated + "/" + asset + ".asset");
            if (data == null)
            {
                data = new TerrainData();
                AssetDatabase.CreateAsset(data, Generated + "/" + asset + ".asset");
            }
            data.heightmapResolution = HeightResolution;
            data.size = new Vector3(area.sizeX, HeightRange, area.sizeZ);
            var heights = new float[HeightResolution, HeightResolution];
            for (int z = 0; z < HeightResolution; z++)
            for (int x = 0; x < HeightResolution; x++)
            {
                float wx = area.minX + x * area.sizeX / (HeightResolution - 1);
                float wz = area.minZ + z * area.sizeZ / (HeightResolution - 1);
                heights[z, x] = Mathf.Clamp01((Height(layout, wx, wz) - BaseY) / HeightRange);
            }
            data.SetHeights(0, 0, heights);

            data.terrainLayers = Layers();
            data.alphamapResolution = PaintResolution;
            var paint = new float[PaintResolution, PaintResolution, LayerNames.Length];
            var detail = new int[PaintResolution, PaintResolution];
            for (int z = 0; z < PaintResolution; z++)
            for (int x = 0; x < PaintResolution; x++)
            {
                float wx = area.minX + (x + .5f) * area.sizeX / PaintResolution;
                float wz = area.minZ + (z + .5f) * area.sizeZ / PaintResolution;
                float edgeNoise = (Mathf.PerlinNoise(wx * .36f + 7f, wz * .36f + 3f) - .5f) * .6f;
                float road = RoadDistance(layout, wx, wz, out _);
                float pad = PadDistance(layout, wx, wz, out var nearest, 3.5f) + edgeNoise * 1.5f;
                float inPad = 1f - Smooth(-1.2f, .6f, pad);
                float dirt = Mathf.Max(1f - Smooth(-.25f, 1f, road + edgeNoise), nearest?.surface == "dirt" ? inPad * .7f : 0);
                float plaza = nearest?.surface == "plaza" ? inPad * .85f : 0;
                float forest = nearest?.surface == "forest" ? (1f - Smooth(-1f, 3f, pad)) * (1f - dirt) : 0;
                // Wet, darker banks along the creek reuse the forest-floor layer (keeps the terrain at 4 layers).
                float creek = CreekDistance(layout, wx, wz, out _);
                if (layout.creek != null) forest = Mathf.Max(forest, (1f - Smooth(layout.creek.width * .5f, layout.creek.width * .5f + layout.creek.bank + 1f, creek + edgeNoise * 2f)) * (1f - dirt));
                plaza *= 1f - dirt * .5f;
                paint[z, x, 1] = dirt;
                paint[z, x, 2] = plaza;
                paint[z, x, 3] = forest;
                paint[z, x, 0] = Mathf.Max(.01f, 1f - dirt - plaza - forest);
                float sum = 0;
                for (int l = 0; l < LayerNames.Length; l++) sum += paint[z, x, l];
                for (int l = 0; l < LayerNames.Length; l++) paint[z, x, l] /= sum;
                // Grass: none on roads or pads, thinning toward their edges.
                float density = Smooth(.3f, 2.3f, road) * Smooth(.5f, 2.5f, pad)
                    * (layout.creek != null ? Smooth(layout.creek.width * .5f + .5f, layout.creek.width * .5f + 2.5f, creek) : 1f);
                float scatter = Mathf.PerlinNoise(wx * .71f + 31f, wz * .71f + 41f);
                detail[z, x] = density > .85f && scatter > .55f ? (scatter > .7f ? 3 : 1) : 0;
            }
            data.SetAlphamaps(0, 0, paint);

            // Existing low-grass mesh from the ArtV001 kit as a detail prototype, not a new model.
            var grass = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/QingxiWorld/Models/ArtV001/SM_LowGrass_LOD0.fbx");
            if (grass == null) throw new FileNotFoundException("Grass detail mesh missing (Git LFS pulled?)", "SM_LowGrass_LOD0.fbx");
            data.SetDetailResolution(PaintResolution, 8);
            data.detailPrototypes = new[] { new DetailPrototype {
                prototype = grass, usePrototypeMesh = true, renderMode = DetailRenderMode.VertexLit, useInstancing = true,
                minWidth = .9f, maxWidth = 1.5f, minHeight = .8f, maxHeight = 1.4f, healthyColor = Color.white, dryColor = Color.white
            }};
            data.SetDetailLayer(0, 0, 0, detail);
            EditorUtility.SetDirty(data);

            var go = Terrain.CreateTerrainGameObject(data);
            go.name = objectName;
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(area.minX, BaseY, area.minZ);
            var terrain = go.GetComponent<Terrain>();
            terrain.heightmapPixelError = 4;
            terrain.basemapDistance = 70;
            terrain.detailObjectDistance = 35;
            terrain.materialTemplate = AssetDatabase.LoadAssetAtPath<Material>("Packages/com.unity.render-pipelines.universal/Runtime/Materials/TerrainLit.mat");
            AssetDatabase.SaveAssets();
            Debug.Log($"QINGXI_VILLAGE_TERRAIN: {area.sizeX}x{area.sizeZ} m, height {data.bounds.min.y + BaseY:F2}..{data.bounds.max.y + BaseY:F2} m, grass cells {detail.Cast<int>().Count(v => v > 0)}");
            return terrain;
        }

        static TerrainLayer[] Layers()
        {
            var result = new TerrainLayer[LayerNames.Length];
            for (int i = 0; i < result.Length; i++)
            {
                string path = Generated + "/TerrainLayer-" + LayerNames[i] + ".asset";
                var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
                if (layer == null) { layer = new TerrainLayer(); AssetDatabase.CreateAsset(layer, path); }
                layer.diffuseTexture = Texture(LayerNames[i], Colors[i], 20261029 + i);
                layer.tileSize = new Vector2(6, 6);
                layer.smoothness = 0; layer.metallic = 0;
                EditorUtility.SetDirty(layer);
                result[i] = layer;
            }
            return result;
        }

        static Texture2D Texture(string name, Color color, int seed)
        {
            string path = Generated + "/Terrain-" + name + ".asset";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
            {
                texture = new Texture2D(128, 128, TextureFormat.RGBA32, true) { name = "Terrain-" + name };
                AssetDatabase.CreateAsset(texture, path);
            }
            var pixels = new Color[128 * 128];
            var rng = new System.Random(seed);
            for (int i = 0; i < pixels.Length; i++)
            {
                float change = (float)rng.NextDouble() * .1f - .05f;
                // URP Terrain Lit reads smoothness from the albedo alpha when there is no mask map: keep it matte.
                pixels[i] = new Color(Mathf.Clamp01(color.r + change), Mathf.Clamp01(color.g + change), Mathf.Clamp01(color.b + change), .08f);
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }
    }
}
