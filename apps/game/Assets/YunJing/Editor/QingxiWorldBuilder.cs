using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace YunJing.Editor
{
    /// <summary>Large-scale spatial preview layered over the existing network development scene.</summary>
    public static class QingxiWorldBuilder
    {
        const string Root = "Assets/YunJing/Generated";
        const string ScenePath = Root + "/QingxiWorldPreview.unity";
        const string Models = "Assets/YunJing/Models/QingxiWorldV1/";

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

        [MenuItem("Yun Jing/Generate Qingxi world preview")]
        public static void Generate()
        {
            ProjectBuilder.Generate();
            // Keep the current development services and player prefab. Replace only small courtyard geometry.
            foreach (string name in new[] { "Courtyard ground", "West wall", "East wall", "North wall",
                "Restored stream", "Bridge", "Stone path" }) Remove(name);

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

            Block("Walkable valley foundation", new Vector3(0,-.35f,0), new Vector3(180,.7f,140), grass);
            Block("Village to aptitude plaza path", new Vector3(0,.02f,14), new Vector3(3.2f,.04f,48), path,false);
            Block("Village to bridge path", new Vector3(15,.02f,5), new Vector3(31,.04f,2.6f),path,false);
            Block("Eastern forest road", new Vector3(50,.02f,5), new Vector3(42,.04f,2.6f),path,false);
            Block("Cave trail", new Vector3(70,.025f,27), new Vector3(2.5f,.05f,48),path,false);
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
                var ramp=Block("Bridge approach " + side,new Vector3(25+side*6.6f,.65f,5),
                    new Vector3(2.6f,.25f,3.2f),path);
                ramp.transform.rotation = Quaternion.Euler(0,0,-side*25);
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

            // These are scale and sightline placeholders, not final house/tree/rock models.
            for(int i=0;i<7;i++)
            {
                float x=-34+i*6;
                Block("Medicinal field blockout " + i,new Vector3(x,.08f,-28),new Vector3(4,.16f,12),field);
            }
            for(int i=0;i<10;i++)
            {
                float x=-54+(i%5)*9, z=-4+(i/5)*12;
                Block("Village house blockout " + i,new Vector3(x,1.7f,z),new Vector3(5,3.4f,4),rock);
                Block("Village roof blockout " + i,new Vector3(x,3.6f,z),new Vector3(6,.45f,5),roof);
            }
            var random=new System.Random(241025);
            for(int i=0;i<54;i++)
            {
                float x=38+(float)random.NextDouble()*48, z=-47+(float)random.NextDouble()*92;
                if (Mathf.Abs(z-5)<5 || (x>68 && z>34)) continue;
                Block("Forest trunk blockout " + i,new Vector3(x,2.4f,z),new Vector3(.7f,4.8f,.7f),bark);
                var crown=GameObject.CreatePrimitive(PrimitiveType.Sphere);
                crown.name="Forest crown blockout " + i;
                crown.transform.position=new Vector3(x,5.9f,z);
                crown.transform.localScale=new Vector3(4.2f,3.2f,4.2f);
                crown.GetComponent<Renderer>().sharedMaterial=woodland;
                UnityEngine.Object.DestroyImmediate(crown.GetComponent<Collider>());
            }
            Block("Cave entrance blockout",new Vector3(73,3.2f,48),new Vector3(10,6.4f,4),rock);
            Block("Cave mouth blockout",new Vector3(73,2.1f,45.9f),new Vector3(3.4f,4.2f,.15f),roof,false);
            for(int i=0;i<8;i++)
            {
                float x=-80+i*21;
                Block("Distant sect ridge blockout " + i,new Vector3(x,10,65),new Vector3(18,20,10),rock);
            }

            var camera=Camera.main;
            if(camera!=null) camera.farClipPlane=300;
            RenderSettings.fogDensity=.004f;
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            AssetDatabase.SaveAssets();
            Debug.Log("Qingxi world preview generated at " + ScenePath);
        }
    }
}
