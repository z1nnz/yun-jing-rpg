using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

namespace YunJing.Editor
{
    /// <summary>Large-scale spatial preview layered over the existing network development scene.</summary>
    public static class QingxiWorldBuilder
    {
        const string Root = "Assets/YunJing/Generated";
        const string ScenePath = Root + "/QingxiWorldPreview.unity";
        const string Models = "Assets/YunJing/Models/QingxiWorldV1/";
        const string CollaboratorModels = "Assets/YunJing/Models/CollaboratorWorldV1/";
        const string ListeningTerraceModel = "Assets/YunJing/Models/QingxiListeningTerraceV1/qingxi-listening-terrace-v1.fbx";

        static Material Surface(string name, Color color)
        {
            string path = Root + "/World-" + name + ".mat";
            var result = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (result == null)
            {
                var shader = Shader.Find("Universal Render Pipeline/Lit");
                if (shader == null) throw new InvalidOperationException("URP Lit shader is unavailable");
                result = new Material(shader);
                AssetDatabase.CreateAsset(result, path);
            }
            result.SetColor("_BaseColor", color);
            EditorUtility.SetDirty(result);
            return result;
        }

        static GameObject Block(string name, Vector3 position, Vector3 size, Material material, bool solid = true)
        {
            var item = GameObject.CreatePrimitive(PrimitiveType.Cube);
            item.name = name;
            item.transform.position = position;
            item.transform.localScale = size;
            item.GetComponent<Renderer>().sharedMaterial = material;
            if (!solid) UnityEngine.Object.DestroyImmediate(item.GetComponent<Collider>());
            return item;
        }

        static GameObject Model(string file, string name, Vector3 position, Func<string, Material> material)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(Models + file);
            if (source == null) throw new FileNotFoundException("Qingxi model missing", Models + file);
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(source);
            instance.name = name;
            instance.transform.position = position;
            foreach (var part in instance.GetComponentsInChildren<Renderer>())
                part.sharedMaterial = material(part.gameObject.name);
            return instance;
        }

        static void Remove(string name)
        {
            var obj = GameObject.Find(name);
            if (obj != null) UnityEngine.Object.DestroyImmediate(obj);
        }

        static GameObject CollaboratorModel(string file, string name, Vector3 position, float scale = 1f, float yaw = 0f)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(CollaboratorModels + file);
            if (source == null) throw new FileNotFoundException("Collaborator model missing", CollaboratorModels + file);
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(source);
            instance.name = name;
            instance.transform.position = position;
            instance.transform.localScale = Vector3.one * scale;
            // Imported Z-up FBX roots may carry a corrective rotation. Keep it
            // when adding the requested world-space yaw.
            instance.transform.rotation = Quaternion.Euler(0, yaw, 0) * source.transform.rotation;
            // FBX source colors are converted to URP materials for this editor preview.
            // Detailed texture, LOD and collider authoring still need an import pass.
            var converted = new Dictionary<Material, Material>();
            foreach (var renderer in instance.GetComponentsInChildren<Renderer>())
            {
                var materials = renderer.sharedMaterials;
                for (int i = 0; i < materials.Length; i++)
                {
                    var original = materials[i];
                    if (original == null) continue;
                    if (!converted.TryGetValue(original, out var replacement))
                    {
                        string key = Path.GetFileNameWithoutExtension(file) + "-" +
                            original.name.Replace(" ", "-").Replace("/", "-").Replace("\\", "-").Replace(":", "-");
                        string path = Root + "/Imported-" + key + ".mat";
                        replacement = AssetDatabase.LoadAssetAtPath<Material>(path);
                        if (replacement == null)
                        {
                            var shader = Shader.Find("Universal Render Pipeline/Lit");
                            if (shader == null) throw new InvalidOperationException("URP Lit shader is unavailable");
                            replacement = new Material(shader);
                            AssetDatabase.CreateAsset(replacement, path);
                        }
                        var color = original.HasProperty("_BaseColor") ? original.GetColor("_BaseColor") :
                            original.HasProperty("_Color") ? original.GetColor("_Color") : Color.white;
                        replacement.SetColor("_BaseColor", color);
                        EditorUtility.SetDirty(replacement);
                        converted.Add(original, replacement);
                    }
                    materials[i] = replacement;
                }
                renderer.sharedMaterials = materials;
            }
            // Place the visual foot on the generated terrain after the FBX's
            // import rotation and requested scale have both been applied.
            // Bridges spanning water keep their authored levels. Stream-bank
            // dressing needs the same grounding as the other placed pieces.
            if (!name.Contains("bridge"))
            {
                var terrain = Terrain.activeTerrain;
                var renderers = instance.GetComponentsInChildren<Renderer>();
                if (terrain != null && renderers.Length > 0)
                {
                    var bounds = renderers[0].bounds;
                    for (int i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
                    var target = terrain.SampleHeight(instance.transform.position) + terrain.transform.position.y;
                    instance.transform.position += Vector3.up * (target - bounds.min.y);
                }
            }
            return instance;
        }

        static void ListeningTerrace(Vector3 position)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(ListeningTerraceModel);
            if (source == null) throw new FileNotFoundException("Listening terrace model missing", ListeningTerraceModel);
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(source);
            instance.name = "Qingxi listening terrace";
            instance.transform.position = position;
            var stone = Surface("TerracePaleStone", new Color(.68f, .67f, .58f));
            var darkStone = Surface("TerraceDarkStone", new Color(.42f, .46f, .43f));
            var timber = Surface("TerraceTimber", new Color(.36f, .27f, .18f));
            var bronze = Surface("TerraceBronze", new Color(.59f, .48f, .29f));
            var plant = Surface("TerracePlant", new Color(.34f, .46f, .26f));
            foreach (var part in instance.GetComponentsInChildren<Renderer>())
            {
                string n = part.gameObject.name;
                part.sharedMaterial = n.Contains("Bamboo") || n.Contains("Flower") || n.Contains("Grass") ? plant :
                    n.Contains("Bronze") || n.Contains("Bell") ? bronze :
                    n.Contains("Timber") || n.Contains("Seat") || n.Contains("Rope") ? timber :
                    n.Contains("Foundation") ? darkStone : stone;
            }
            // Only the principal stone structure receives collision. Thin ornament meshes stay decorative.
            foreach (var filter in instance.GetComponentsInChildren<MeshFilter>())
            {
                string n = filter.gameObject.name;
                if (!n.Contains("Foundation") && !n.Contains("Paving") && !n.Contains("EntryStep")) continue;
                var collision = filter.gameObject.AddComponent<MeshCollider>();
                collision.sharedMesh = filter.sharedMesh;
            }
        }

        [MenuItem("Yun Jing/Generate Qingxi world preview")]
        public static void Generate()
        {
            ProjectBuilder.Generate();
            // Keep the current development services and player prefab. Replace only small courtyard geometry.
            foreach (string name in new[] { "Courtyard ground", "West wall", "East wall", "North wall",
                "Restored stream", "Bridge", "Stone path", "Broken array" }) Remove(name);

            var grass = Surface("ValleyGrass", new Color(.32f,.43f,.28f));
            var woodland = Surface("Woodland", new Color(.19f,.32f,.23f));
            var water = Surface("QingxiWater", new Color(.22f,.54f,.59f));
            var path = Surface("StonePath", new Color(.63f,.59f,.46f));
            var rock = Surface("Rock", new Color(.44f,.47f,.43f));
            var bark = Surface("AncientBark", new Color(.29f,.25f,.18f));
            var leaf = Surface("AncientLeaf", new Color(.35f,.48f,.27f));
            var timber = Surface("BridgeTimber", new Color(.24f,.27f,.22f));
            var roof = Surface("HouseRoof", new Color(.16f,.27f,.29f));
            var field = Surface("Field", new Color(.39f,.31f,.20f));

            // One terrain owns ground height and paint. Roads and forks are a
            // union mask within it, not overlapping surface cubes.
            QingxiEntranceTerrain.Create();
            ListeningTerrace(new Vector3(-8, 0, -15));
            Block("Qingxi river channel", new Vector3(25,.03f,0), new Vector3(10,.06f,139),water,false);
            // A visible river can be crossed only at the bridge in this first playable layout.
            var south=Block("River crossing boundary south",new Vector3(25,1,-33.75f),new Vector3(.4f,2,72.5f),water);
            var north=Block("River crossing boundary north",new Vector3(25,1,38.75f),new Vector3(.4f,2,62.5f),water);
            south.GetComponent<Renderer>().enabled=false;
            north.GetComponent<Renderer>().enabled=false;

            var bridge = Model("qingxi-timber-bridge-v1.fbx","Qingxi timber bridge",new Vector3(25,0,5),
                n => n.Contains("PaleBridgeStone") ? rock : timber);
            // Visual planks have deliberate gaps. A separate collision deck keeps movement predictable.
            var deck = Block("Bridge walk collision",new Vector3(25,1.45f,5),new Vector3(10.8f,.28f,3.2f),path);
            deck.GetComponent<Renderer>().enabled = false;
            foreach (int side in new[] {-1,1})
            {
                var ramp=Block("Bridge approach " + side,new Vector3(25+side*7.7f,.8f,5),
                    new Vector3(4.8f,.25f,3.2f),path);
                ramp.transform.rotation = Quaternion.Euler(0,0,-side*18);
            }

            Model("qingxi-sacred-tree-v1.fbx","Village sacred tree",new Vector3(-13,0,27),
                n => n.Contains("Canopy") ? leaf : n.Contains("Ribbon") ? roof : bark);
            var trunk=Block("Sacred tree collision",new Vector3(-13,2.2f,27),new Vector3(1.8f,4.4f,1.8f),bark);
            trunk.GetComponent<Renderer>().enabled=false;

            // Original plaza already has its own AI three-view and Blender source.
            var plazaSource=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/AptitudePlazaV1/aptitude-plaza-v1.fbx");
            if (plazaSource!=null)
            {
                var plaza=(GameObject)PrefabUtility.InstantiatePrefab(plazaSource);
                plaza.name="Aptitude plaza preview"; plaza.transform.position=new Vector3(0,.06f,29);
                foreach(var part in plaza.GetComponentsInChildren<Renderer>()) part.sharedMaterial=rock;
            }
            else Block("Aptitude plaza placeholder",new Vector3(0,.08f,29),new Vector3(17,.15f,17),rock);

            // The incoming full TownLayout is deliberately kept in the Blender
            // composition: 906k triangles and 3,877 meshes are not mobile-ready.
            // A bounded selection of its constituent props replaces the v1 grayboxes.
            for(int i=0;i<7;i++)
            {
                float x=-34+i*6;
                Block("Medicinal field blockout " + i,new Vector3(x,.08f,-28),new Vector3(4,.16f,12),field);
            }
            CollaboratorModel("StarterHouse_v004.fbx", "Riverside starter house", new Vector3(-32,.05f,-9));
            CollaboratorModel("StarterHouse_v004.fbx", "Plaza-side starter house", new Vector3(-35,.05f,14),.90f,95f);
            CollaboratorModel("StoneArchBridge_v001.fbx", "South stone bridge", new Vector3(25,.03f,-36),1f,90f);
            CollaboratorModel("MountainStreamBend_v001.fbx", "Eastern stream bend", new Vector3(52,.04f,-26));
            CollaboratorModel("MountainStonePath_v001.fbx", "Cave stone approach", new Vector3(70,.03f,36));
            CollaboratorModel("MountainStoneStairs_v001.fbx", "Northern stone ascent", new Vector3(5,.03f,48));
            CollaboratorModel("CliffBoardwalk_v001.fbx", "Northern lookout", new Vector3(39,2.2f,51));
            CollaboratorModel("QCaveEntrance_v003.fbx", "Eastern cave entrance", new Vector3(73,.03f,48),1f,180f);
            CollaboratorModel("SectGate_v001.fbx", "Northern sect gate silhouette", new Vector3(7,.05f,61),.8f,180f);
            foreach (var cliff in new[] {new Vector3(-70,2,55),new Vector3(70,2,55),new Vector3(78,2,46)})
                CollaboratorModel("LayeredCliff_v001.fbx", "Layered cliff preview", cliff,.58f);
            var random=new System.Random(241025);
            for(int i=0;i<12;i++)
            {
                float x=42+(float)random.NextDouble()*43, z=-45+(float)random.NextDouble()*85;
                if (Mathf.Abs(z-5)<6) z+=10;
                CollaboratorModel("CommonPine_v001.fbx", "Eastern pine " + i,new Vector3(x,.03f,z),
                    .75f+(float)random.NextDouble()*.3f,random.Next(360));
            }
            foreach (var point in new[] {new Vector3(47,.03f,-32),new Vector3(76,.03f,-18),new Vector3(52,.03f,28)})
                CollaboratorModel("BambooClump_v001.fbx", "Eastern bamboo",point,.72f);
            foreach (var point in new[] {new Vector3(41,.03f,-12),new Vector3(73,.03f,25),new Vector3(-6,.03f,39)})
                CollaboratorModel("MossBoulderSet_v001.fbx", "Mossy boulder",point,.9f);

            var camera=Camera.main;
            if(camera!=null) camera.farClipPlane=300;
            RenderSettings.fogDensity=.004f;
            BakeEntranceNavMesh();
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            AssetDatabase.SaveAssets();
            Debug.Log("Qingxi world preview generated at " + ScenePath);
        }

        static void BakeEntranceNavMesh()
        {
            Physics.SyncTransforms();
            var bounds = new Bounds(new Vector3(0, 2, 0), new Vector3(180, 16, 140));
            var sources = new List<NavMeshBuildSource>();
            NavMeshBuilder.CollectSources(bounds, ~0, NavMeshCollectGeometry.PhysicsColliders,
                0, new List<NavMeshBuildMarkup>(), sources);
            var settings = NavMesh.GetSettingsByID(0);
            settings.agentRadius = .35f;
            settings.agentHeight = 1.4f;
            settings.agentClimb = .3f;
            settings.agentSlope = 35f;
            var data = NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, Vector3.zero, Quaternion.identity);
            if (data == null) throw new InvalidOperationException("Entrance NavMesh bake failed");
            const string path = "Assets/YunJing/Generated/QingxiEntranceNavMesh.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(data, path);
            Debug.Log($"QINGXI_ENTRANCE_NAVMESH: {sources.Count} collider sources");
        }
    }
}
