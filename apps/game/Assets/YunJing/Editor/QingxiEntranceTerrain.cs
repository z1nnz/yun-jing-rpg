using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace YunJing.Editor
{
    // The route graph is the one source for ground height, paint, grass exclusion
    // and the grounding acceptance config. Generated Terrain assets are disposable.
    public static class QingxiEntranceTerrain
    {
        const string Generated = "Assets/YunJing/Generated";
        const int HeightResolution = 257;
        const int PaintResolution = 256;
        const float MinX = -90f, MinZ = -70f, SizeX = 180f, SizeZ = 140f;
        const float BaseY = -2f, HeightRange = 8f;

        [Serializable] public class Node { public string id; public float x, z; }
        [Serializable] public class Edge { public string id, from, to, surface; public float width; }
        [Serializable] public class Checkpoint { public string name, node; }
        [Serializable] public class Graph
        {
            public int version;
            public Node[] nodes;
            public Edge[] edges;
            public Checkpoint[] checkpoints;
            public string[] route;
        }

        static readonly Color[] Colors = {
            new Color(.39f, .49f, .32f), // grass
            new Color(.57f, .43f, .29f), // packed earth
            new Color(.49f, .48f, .42f), // gravel
            new Color(.31f, .40f, .35f)  // wet bank
        };
        static readonly string[] LayerNames = { "Meadow", "PackedEarth", "Gravel", "WetBank" };

        public static Graph LoadGraph()
        {
            var file = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../tools/qingxi-terrain/routes.json"));
            if (!File.Exists(file)) throw new FileNotFoundException("Qingxi route graph missing", file);
            var graph = JsonUtility.FromJson<Graph>(File.ReadAllText(file));
            if (graph == null || graph.version != 1 || graph.nodes == null || graph.edges == null)
                throw new InvalidDataException("Qingxi route graph is invalid");
            var nodes = graph.nodes.ToDictionary(n => n.id);
            foreach (var edge in graph.edges)
                if (edge.width <= 0 || !nodes.ContainsKey(edge.from) || !nodes.ContainsKey(edge.to))
                    throw new InvalidDataException("Invalid Qingxi road: " + edge.id);
            return graph;
        }

        static float Smooth(float a, float b, float value)
        {
            float t = Mathf.Clamp01((value - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        static float SegmentDistance(float x, float z, Node a, Node b)
        {
            var ab = new Vector2(b.x - a.x, b.z - a.z);
            var ap = new Vector2(x - a.x, z - a.z);
            float t = ab.sqrMagnitude < .0001f ? 0 : Mathf.Clamp01(Vector2.Dot(ap, ab) / ab.sqrMagnitude);
            return (ap - ab * t).magnitude;
        }

        // Union of every branch, including Y and T junctions. No road strips
        // are laid over each other and grass sees the same exterior boundary.
        public static float SignedRoadDistance(Graph graph, float x, float z)
        {
            var nodes = graph.nodes.ToDictionary(n => n.id);
            float distance = float.MaxValue;
            foreach (var edge in graph.edges)
                distance = Mathf.Min(distance, SegmentDistance(x, z, nodes[edge.from], nodes[edge.to]) - edge.width * .5f);
            return distance;
        }

        static float RiverDistance(float x, float z) => Mathf.Abs(x - (25f + .7f * Mathf.Sin(z * .045f)));

        static float Height(Graph graph, float x, float z)
        {
            float land = .04f + .32f * (Mathf.PerlinNoise(x * .026f + 13f, z * .026f + 5f) - .5f)
                + .12f * (Mathf.PerlinNoise(x * .09f + 73f, z * .09f + 19f) - .5f);
            float river = RiverDistance(x, z);
            land = Mathf.Lerp(-.8f, land, Smooth(4.5f, 9f, river));
            // Flatten each branch and its junction as a single mask; fade the
            // adjustment into the surrounding slope over two metres.
            float road = SignedRoadDistance(graph, x, z);
            land = Mathf.Lerp(.04f, land, Smooth(0f, 2.1f, road));
            foreach (var pad in new[] {
                new Vector4(-32, -9, 4.8f, 4f), new Vector4(-35, 14, 4.8f, 4f),
                new Vector4(-13, 27, 3.2f, 3.2f), new Vector4(-8, -15, 5f, 5f)
            })
            {
                float edge = Mathf.Max(Mathf.Abs(x - pad.x) - pad.z, Mathf.Abs(z - pad.y) - pad.w);
                land = Mathf.Lerp(.04f, land, Smooth(0f, 2.5f, edge));
            }
            return land;
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
                float change = (float)rng.NextDouble() * .12f - .06f;
                pixels[i] = new Color(Mathf.Clamp01(color.r + change), Mathf.Clamp01(color.g + change),
                    Mathf.Clamp01(color.b + change), 1);
            }
            texture.SetPixels(pixels);
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.Apply(true);
            EditorUtility.SetDirty(texture);
            return texture;
        }

        static TerrainLayer[] Layers()
        {
            var result = new TerrainLayer[LayerNames.Length];
            for (int i = 0; i < result.Length; i++)
            {
                string path = Generated + "/TerrainLayer-" + LayerNames[i] + ".asset";
                var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
                if (layer == null)
                {
                    layer = new TerrainLayer();
                    AssetDatabase.CreateAsset(layer, path);
                }
                layer.diffuseTexture = Texture(LayerNames[i], Colors[i], 20261029 + i);
                layer.tileSize = new Vector2(7, 7);
                EditorUtility.SetDirty(layer);
                result[i] = layer;
            }
            return result;
        }

        public static Terrain Create(string name = "Qingxi entrance terrain")
        {
            var graph = LoadGraph();
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(Generated + "/QingxiEntranceTerrain.asset");
            if (data == null)
            {
                data = new TerrainData();
                AssetDatabase.CreateAsset(data, Generated + "/QingxiEntranceTerrain.asset");
            }
            data.heightmapResolution = HeightResolution;
            data.size = new Vector3(SizeX, HeightRange, SizeZ);
            var heights = new float[HeightResolution, HeightResolution];
            for (int z = 0; z < HeightResolution; z++)
            for (int x = 0; x < HeightResolution; x++)
            {
                float wx = MinX + x * SizeX / (HeightResolution - 1);
                float wz = MinZ + z * SizeZ / (HeightResolution - 1);
                heights[z, x] = Mathf.Clamp01((Height(graph, wx, wz) - BaseY) / HeightRange);
            }
            data.SetHeights(0, 0, heights);
            data.terrainLayers = Layers();
            data.alphamapResolution = PaintResolution;
            var paint = new float[PaintResolution, PaintResolution, LayerNames.Length];
            for (int z = 0; z < PaintResolution; z++)
            for (int x = 0; x < PaintResolution; x++)
            {
                float wx = MinX + (x + .5f) * SizeX / PaintResolution;
                float wz = MinZ + (z + .5f) * SizeZ / PaintResolution;
                float edgeNoise = (Mathf.PerlinNoise(wx * .36f + 7f, wz * .36f + 3f) - .5f) * .5f;
                float road = SignedRoadDistance(graph, wx, wz) + edgeNoise;
                float dirt = 1f - Smooth(-.25f, 1f, road);
                float gravel = .32f * (Smooth(-.4f, .3f, road) - Smooth(.8f, 2f, road));
                float wet = (1f - Smooth(5f, 9f, RiverDistance(wx, wz))) * (1f - dirt);
                paint[z, x, 0] = Mathf.Max(.01f, 1f - dirt - gravel - wet);
                paint[z, x, 1] = Mathf.Max(0, dirt);
                paint[z, x, 2] = Mathf.Max(0, gravel);
                paint[z, x, 3] = Mathf.Max(0, wet);
                float sum = 0;
                for (int layer = 0; layer < LayerNames.Length; layer++) sum += paint[z, x, layer];
                for (int layer = 0; layer < LayerNames.Length; layer++) paint[z, x, layer] /= sum;
            }
            data.SetAlphamaps(0, 0, paint);

            // Existing low-grass model is a detail prototype, not a new model.
            var grass = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/QingxiWorld/Models/ArtV001/SM_LowGrass_LOD0.fbx");
            if (grass != null)
            {
                data.SetDetailResolution(PaintResolution, 8);
                data.detailPrototypes = new[] { new DetailPrototype {
                    prototype = grass, usePrototypeMesh = true, renderMode = DetailRenderMode.Grass,
                    minWidth = .4f, maxWidth = .8f, minHeight = .35f, maxHeight = .8f,
                    healthyColor = Color.white, dryColor = Color.white
                }};
                var detail = new int[PaintResolution, PaintResolution];
                for (int z = 0; z < PaintResolution; z++)
                for (int x = 0; x < PaintResolution; x++)
                {
                    float wx = MinX + (x + .5f) * SizeX / PaintResolution;
                    float wz = MinZ + (z + .5f) * SizeZ / PaintResolution;
                    float road = SignedRoadDistance(graph, wx, wz);
                    float density = Smooth(.3f, 2.3f, road) * Smooth(7f, 10f, RiverDistance(wx, wz));
                    float scatter = Mathf.PerlinNoise(wx * .71f + 31f, wz * .71f + 41f);
                    detail[z, x] = density > .85f && scatter > .67f ? 1 : 0;
                }
                data.SetDetailLayer(0, 0, 0, detail);
            }
            EditorUtility.SetDirty(data);
            var go = Terrain.CreateTerrainGameObject(data);
            go.name = name;
            go.transform.position = new Vector3(MinX, BaseY, MinZ);
            var terrain = go.GetComponent<Terrain>();
            terrain.heightmapPixelError = 4;
            terrain.basemapDistance = 80;
            terrain.detailObjectDistance = 38;
            AssetDatabase.SaveAssets();
            return terrain;
        }
    }
}
