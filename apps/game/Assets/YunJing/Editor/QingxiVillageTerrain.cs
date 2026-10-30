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
            public bool sourceEnd = true;   // false when the creek carries on into the next block (D1 into D3)
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
            public Flat[] flats;              // ground levelled under built works that are not on a pad (the old channel)
            public float relief;              // metres of broad rolling relief on open ground (roads, pads, creek stay level)
            public float terrace;             // Liyue-style terrace step (m) on the relief; 0 for none
        }
        [Serializable] public class Flat { public string id, note; public float x, z, halfX, halfZ, height, blend = 1.5f; }
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
                if (d < best) { best = d; centreLand = LandAt(layout, q.x, q.y); }
            }
            return best;
        }

        /// <summary>Height of the water surface at a point on (or near) the creek centre line.</summary>
        public static float WaterHeight(Layout layout, float x, float z)
        {
            CreekDistance(layout, x, z, out float land);
            return land - layout.creek.depth + layout.creek.waterLevel;
        }

        // Seven grounds, after Liyue's valleys (docs/execution/liyue-terrain-standard.md): lush and sun-dried meadow in
        // patches, packed earth on the paths, stone slabs near the village, leaf-litter forest floor, creek gravel, and
        // the warm ochre rock that shows where the ground is too steep to hold grass.
        static readonly string[] LayerNames = { "VillageMeadow", "VillagePackedEarth", "VillagePlazaStone", "VillageForestFloor", "MeadowDry", "CreekGravel", "OchreRock" };
        static readonly Color[] Colors = {
            new Color(.38f, .50f, .29f), new Color(.55f, .43f, .29f), new Color(.55f, .53f, .48f), new Color(.29f, .30f, .20f),
            new Color(.60f, .57f, .33f), new Color(.52f, .50f, .45f), new Color(.66f, .50f, .34f)
        };
        static readonly string[] Kinds = { "grass", "earth", "slab", "litter", "grass", "gravel", "rock" };
        static readonly float[] Tiles = { 5, 4, 4, 4, 6, 2.5f, 7 };

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
        /// <summary>The planned land height eased to the shared world height near the block edge, as the terrain is:
        /// the creek and its river tiles follow this, so a creek crossing into the next block meets it at the same level.</summary>
        internal static float LandAt(Layout layout, float x, float z)
        {
            var area = layout.bounds;
            float border = Mathf.Min(Mathf.Min(x - area.minX, area.minX + area.sizeX - x), Mathf.Min(z - area.minZ, area.minZ + area.sizeZ - z));
            return Mathf.Lerp(WorldBase(x, z), BaseHeight(layout, x, z), Smooth(1f, 12f, border));
        }

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
            // Broad relief: two octaves of rolling hills; on terraced ground the slopes break into soft steps.
            if (layout.relief > 0)
            {
                float hill = (Mathf.PerlinNoise(x * .018f + 101f, z * .018f + 57f) - .5f) * 2f * .7f + (Mathf.PerlinNoise(x * .045f + 13f, z * .045f + 91f) - .5f) * 2f * .3f;
                float rise = hill * layout.relief;
                if (layout.terrace > 0)
                {
                    float steps = rise / layout.terrace, floor = Mathf.Floor(steps), t = steps - floor;
                    rise = Mathf.Lerp(rise, (floor + Mathf.SmoothStep(0, 1, Mathf.Clamp01((t - .65f) / .35f))) * layout.terrace, .7f);
                }
                h += rise;
            }
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
            // Levelled strips under works that cross the creek bank (joshsu54's old channel): after the creek, so the
            // intake end reaches into the water at its stated height.
            foreach (var f in layout.flats ?? new Flat[0])
            {
                float edge = Mathf.Max(Mathf.Abs(x - f.x) - f.halfX, Mathf.Abs(z - f.z) - f.halfZ);
                h = Mathf.Lerp(f.height, h, Smooth(0f, f.blend, edge));
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
                // Irregular paths: the worn width wanders along the road and the edge is ragged, grass creeping in.
                float wander = (Mathf.PerlinNoise(wx * .09f + 211f, wz * .09f + 17f) - .5f) * 1.1f;
                float ragged = (Mathf.PerlinNoise(wx * 1.3f + 5f, wz * 1.3f + 77f) - .5f) * .55f;
                float worn = road + wander + ragged;
                float dirt = Mathf.Max(1f - Smooth(-.35f, .9f, worn), nearest?.surface == "dirt" ? inPad * .7f : 0);
                // Stone slabs on the village roads (A1 only), broken into stretches with earth between them.
                bool village = area.minX == -50 && area.minZ == -50;
                float slabRun = Smooth(.55f, .7f, Mathf.PerlinNoise(wx * .06f + 300f, wz * .06f + 300f));
                float slabs = village ? dirt * slabRun * (1f - Smooth(-.9f, .2f, worn + .4f)) : 0;
                float plaza = Mathf.Max(nearest?.surface == "plaza" ? inPad * .85f : 0, slabs);
                float forest = nearest?.surface == "forest" ? (1f - Smooth(-1f, 3f, pad)) * (1f - dirt) : 0;
                // Creek banks: gravel at the water's edge, darker leaf-litter and moss further up the bank.
                float creek = CreekDistance(layout, wx, wz, out _);
                float gravel = 0;
                if (layout.creek != null)
                {
                    float half = layout.creek.width * .5f;
                    gravel = (1f - Smooth(half + .2f, half + 1.6f, creek + edgeNoise * 2f)) * (1f - dirt);
                    forest = Mathf.Max(forest, (1f - Smooth(half + 1f, half + layout.creek.bank + 2.5f, creek + edgeNoise * 3f)) * (1f - dirt) * (1f - gravel));
                }
                // Steep ground shows the warm ochre rock; open meadow alternates lush and sun-dried patches.
                float step = area.sizeX / PaintResolution;
                float slope = Mathf.Max(Mathf.Abs(Height(layout, wx + step, wz) - Height(layout, wx - step, wz)), Mathf.Abs(Height(layout, wx, wz + step) - Height(layout, wx, wz - step))) / (2 * step);
                float rock = Smooth(.45f, .8f, slope + edgeNoise * .3f) * (1f - dirt);
                float dryPatch = Smooth(.5f, .68f, Mathf.PerlinNoise(wx * .035f + 71f, wz * .035f + 9f) + edgeNoise * .4f);
                plaza *= 1f - dirt * .5f;
                float open = Mathf.Max(0, 1f - dirt - plaza - forest - gravel - rock);
                paint[z, x, 1] = dirt;
                paint[z, x, 2] = plaza;
                paint[z, x, 3] = forest;
                paint[z, x, 5] = gravel;
                paint[z, x, 6] = rock;
                paint[z, x, 4] = open * dryPatch * .85f;
                paint[z, x, 0] = Mathf.Max(.01f, open - paint[z, x, 4]);
                float sum = 0;
                for (int l = 0; l < LayerNames.Length; l++) sum += paint[z, x, l];
                for (int l = 0; l < LayerNames.Length; l++) paint[z, x, l] /= sum;
                // Grass: none on roads or pads, thinning toward their edges.
                float density = Smooth(.1f, 1.8f, worn) * Smooth(.5f, 2.5f, pad) * (1f - rock) * (1f - gravel)
                    * (layout.creek != null ? Smooth(layout.creek.width * .5f + .5f, layout.creek.width * .5f + 2.5f, creek) : 1f);
                float scatter = Mathf.PerlinNoise(wx * .71f + 31f, wz * .71f + 41f);
                detail[z, x] = density > .7f && scatter > .42f ? (scatter > .66f ? 4 : scatter > .54f ? 2 : 1) : 0;
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
                layer.diffuseTexture = Texture(LayerNames[i], Colors[i], 20261029 + i, Kinds[i], out var relief);
                layer.normalMapTexture = NormalMap(LayerNames[i], relief, Kinds[i] == "slab" || Kinds[i] == "rock" ? 2.2f : Kinds[i] == "grass" ? .5f : 1.4f);
                layer.tileSize = new Vector2(Tiles[i], Tiles[i]);
                layer.smoothness = 0; layer.metallic = 0;
                EditorUtility.SetDirty(layer);
                result[i] = layer;
            }
            return result;
        }

        // A tileable ground texture drawn from noise: every kind has its own pattern so the ground reads as grass,
        // earth, slabs, leaf litter, gravel or rock up close, not as one flat colour. `relief` is the matching height
        // field (raised slabs and pebbles, sunken joints) for the normal map.
        static Texture2D Texture(string name, Color color, int seed, string kind, out float[] relief)
        {
            int N = kind == "slab" || kind == "gravel" ? 512 : 256;
            string path = Generated + "/Terrain-" + name + ".asset";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null || texture.width != N)
            {
                if (texture != null) AssetDatabase.DeleteAsset(path);
                texture = new Texture2D(N, N, TextureFormat.RGBA32, true) { name = "Terrain-" + name };
                AssetDatabase.CreateAsset(texture, path);
            }
            var rng = new System.Random(seed);
            float ox = rng.Next(1000), oz = rng.Next(1000);
            // Tileable noise: blend four copies shifted by one tile, so opposite edges meet without bending the pattern.
            float Tile(float u, float v, float freq)
            {
                float Nz(float x, float y) => Mathf.PerlinNoise(ox + x * freq, oz + y * freq);
                return Nz(u, v) * (1 - u) * (1 - v) + Nz(u - 1, v) * u * (1 - v) + Nz(u, v - 1) * (1 - u) * v + Nz(u - 1, v - 1) * u * v;
            }
            float Fbm(float u, float v, float f) => Tile(u, v, f) * .55f + Tile(u, v, f * 2.1f) * .3f + Tile(u, v, f * 4.3f) * .15f;
            // Cell centres (wrapping) for pebbles, slabs and leaves; z is the cell's own shade. Slabs are jittered off
            // a loose grid so they are irregular but similar in size, like laid flagstones.
            int count = kind == "gravel" ? 240 : 70;
            Vector3[] cells;
            if (kind == "slab")
            {
                int g = 10; cells = new Vector3[g * 11];
                for (int i = 0; i < cells.Length; i++)
                    cells[i] = new Vector3(((i % g) + .5f + ((float)rng.NextDouble() - .5f) * .8f) / g, ((i / g) + .5f + ((float)rng.NextDouble() - .5f) * .8f) / 11f, (float)rng.NextDouble());
            }
            else cells = Enumerable.Range(0, count).Select(_ => new Vector3((float)rng.NextDouble(), (float)rng.NextDouble(), (float)rng.NextDouble())).ToArray();
            for (int i = 0; i < cells.Length; i++) cells[i] = new Vector3(Mathf.Repeat(cells[i].x, 1), Mathf.Repeat(cells[i].y, 1), cells[i].z);
            float Distance(float u, float v, Vector3 k)
            {
                float du = Mathf.Abs(u - k.x), dv = Mathf.Abs(v - k.y); du = Mathf.Min(du, 1 - du); dv = Mathf.Min(dv, 1 - dv);
                return Mathf.Sqrt(du * du + dv * dv);
            }
            var pixels = new Color[N * N];
            relief = new float[N * N];
            for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float u = x / (float)N, v = y / (float)N, light = Fbm(u, v, 6) - .5f, tint = Fbm(u, v, 2.5f) - .5f;
                float d1 = 9, d2 = 9; var cell = cells[0];
                foreach (var k in cells) { float d = Distance(u, v, k); if (d < d1) { d2 = d1; d1 = d; cell = k; } else if (d < d2) d2 = d; }
                Color c = color; float h = .5f + light * .3f;
                switch (kind)
                {
                    case "grass":   // fine speckle of blades in every direction, darker tufts, a warmer hue in places
                        float speck = Tile(u, v, 64) - .5f, tuft = Tile(u, v, 18) - .5f;
                        c = color * (1 + light * .35f + speck * .3f + tuft * .2f) + new Color(tint * .08f, tint * .05f, -tint * .03f);
                        h = .5f + tuft * .6f + speck * .3f;
                        break;
                    case "earth":   // packed earth with clumps and a few small stones
                        c = color * (1 + light * .45f + (Tile(u, v, 48) - .5f) * .2f);
                        h = .45f + light * .5f;
                        // A few small stones, different sizes, only slightly paler than the earth.
                        if (cell.z > .45f && d1 < .004f + cell.z * .006f) { c = Color.Lerp(c, color * (1.05f + cell.z * .15f), .55f); h += .3f; }
                        break;
                    case "slab":    // laid flagstones: each its own shade and wear, dark soft joints, moss in some of them
                        float joint = Mathf.SmoothStep(0, 1, Mathf.Clamp01((d2 - d1) / .018f));   // 0 in the joint, 1 on the stone
                        var shade = new Color(.92f + cell.z * .16f, .92f + cell.z * .12f, .9f + (1 - cell.z) * .12f);   // warm or cool stones
                        float wear = Fbm(u + cell.z, v - cell.z, 9) - .5f, grime = Tile(u, v, 30) - .5f;
                        var stone = new Color(color.r * shade.r, color.g * shade.g, color.b * shade.b) * (1 + wear * .45f + grime * .15f);
                        stone *= Mathf.Lerp(.82f, 1f, Mathf.Clamp01((d2 - d1) / .05f));   // edges worn darker
                        var gap = Tile(u, v, 22) > .58f ? new Color(.26f, .32f, .18f) : new Color(.24f, .21f, .17f);   // moss or soil in the joint
                        c = Color.Lerp(gap, stone, joint);
                        h = joint * (.75f + wear * .25f) + (1 - joint) * .1f;
                        break;
                    case "litter":  // leaf litter and moss over dark soil
                        c = color * (1 + light * .5f);
                        if (Tile(u, v, 70) > .6f) { c = Color.Lerp(c, cell.z > .5f ? new Color(.52f, .38f, .2f) : new Color(.35f, .42f, .22f), .4f); h += .2f; }   // small leaves, not camouflage blotches
                        break;
                    case "gravel":  // rounded pebbles of several greys
                        float pebble = Mathf.Clamp01((1 - d1 / (.016f + cell.z * .018f)) * 1.6f);   // 4-9 cm pebbles of mixed sizes
                        c = Color.Lerp(color * (.72f + light * .2f), color * (.85f + cell.z * .35f), pebble) * (1 + light * .2f);
                        h = Mathf.Sqrt(pebble) * .9f;
                        break;
                    case "rock":    // ochre rock with horizontal strata
                        float band = Mathf.Sin((v + light * .08f) * Mathf.PI * 2 * 9) * .5f + .5f;
                        c = color * (.82f + band * .22f + light * .35f);
                        h = band * .6f + light * .5f;
                        break;
                }
                // URP Terrain Lit reads smoothness from the albedo alpha when there is no mask map: keep it matte.
                pixels[y * N + x] = new Color(Mathf.Clamp01(c.r), Mathf.Clamp01(c.g), Mathf.Clamp01(c.b), .06f);
                relief[y * N + x] = h;
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.anisoLevel = 4;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }

        // Tangent-space normal map from a wrapped height field (R = x, G = y, B = z, A = 1; the URP terrain shader
        // unpacks this layout), so slab joints, pebbles and strata catch the light.
        static Texture2D NormalMap(string name, float[] relief, float strength)
        {
            int N = (int)Mathf.Sqrt(relief.Length);
            string path = Generated + "/TerrainNormal-" + name + ".asset";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null || texture.width != N)
            {
                if (texture != null) AssetDatabase.DeleteAsset(path);
                texture = new Texture2D(N, N, TextureFormat.RGBA32, true, true) { name = "TerrainNormal-" + name };
                AssetDatabase.CreateAsset(texture, path);
            }
            float H(int x, int y) => relief[((y + N) % N) * N + (x + N) % N];
            var pixels = new Color[N * N];
            for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float dx = (H(x + 1, y) - H(x - 1, y)) * strength, dy = (H(x, y + 1) - H(x, y - 1)) * strength;
                var n = new Vector3(-dx, -dy, 1).normalized;
                pixels[y * N + x] = new Color(n.x * .5f + .5f, n.y * .5f + .5f, n.z * .5f + .5f, 1);
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.anisoLevel = 4;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }
    }
}
