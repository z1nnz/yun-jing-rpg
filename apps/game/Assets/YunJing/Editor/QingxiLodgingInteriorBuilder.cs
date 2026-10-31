using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace YunJing.Editor
{
    // The newcomer's own territory (K23; a private scene, entered through the lodging door with a fade): the old
    // house Qingxi lends to newcomers, and its walled backyard. Inside: joshsu54's disciple bed, storage chest and
    // meditation cushion (Johnnnny0823's qi breathing drill) in a graybox room. Out the back door: two spirit
    // fields (QingxiTerritoryFields, planted and harvested through the server) and Johnnnny0823's agility post
    // for the block drill. The front door walks back out into the shared world. Room and yard walls are
    // placeholders until the interior kit (Codex C2) arrives.
    public static class QingxiLodgingInteriorBuilder
    {
        public const string ScenePath = "Assets/YunJing/Generated/QingxiLodgingInterior.unity";
        const string Models = "Assets/YunJing/Models/LodgingInterior";   // copied from art/incoming/dondon, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/Collaborators";
        const float W = 7f, D = 5f, H = 3.2f;   // room width (x), depth (z), height
        const float TeaStoveX = .3f, TeaStoveZ = 2.0f;   // TI_TeaStove: back wall between the lamp and the chest

        public static void Generate()
        {
            QingxiUrpUpgrade.EnsurePipeline();
            CopyFurniture();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var room = new GameObject("QingxiLodgingInterior").transform;
            Shell(room);
            Lights(room);
            Yard(room, out var fields, out var practicePost);
            TerritorySlots(room);

            var bed = Furniture("DiscipleBed", "DiscipleBed_v001", room, new Vector3(-W / 2 + .75f, 0, 1.0f), 90f);
            var chest = Furniture("StorageChest", "StorageChest_v001", room, new Vector3(W / 2 - .9f, 0, D / 2 - .6f), 180f);
            var cushion = Furniture("MeditationCushion", "MeditationCushion_v001", room, new Vector3(1.2f, 0, -.2f), 0f);

            var exit = new GameObject("ExitDoor_Lodging").transform; exit.SetParent(room, false);
            exit.localPosition = new Vector3(0, 0, -D / 2 + .7f); exit.localRotation = Quaternion.Euler(0, 180, 0);

            var player = QingxiNoviceVillageBuilder.Player(room, new Vector3(0, .05f, -D / 2 + 1.2f));
            var walker = player.GetComponent<global::QingxiWorld.QingxiFirstPerson>();
            walker.useDesignedHud = true;
            walker.spotNames = new[] { "我的領地" };
            walker.spotPositions = new[] { new Vector3(0, .05f, -D / 2 + 1.2f) };
            walker.spotYaws = new[] { 0f };
            walker.pointsOfInterest = new Transform[0];
            var foraging = player.AddComponent<QingxiLocalForaging>();
            foraging.herbNodes = new Transform[0]; foraging.clueNodes = new Transform[0];
            var stations = player.AddComponent<QingxiAbcStations>();
            stations.exitDoor = exit; stations.bed = bed.transform; stations.chest = chest.transform; stations.walker = walker;
            var training = player.AddComponent<QingxiTrainingPractice>();
            training.qiPost = cushion.transform; training.qiLabel = "蒲團"; training.walker = walker;
            training.blockPost = practicePost;
            stations.fields = fields;
            var teaStove = new GameObject("TeaStove_Station").transform; teaStove.SetParent(room, false);
            teaStove.localPosition = new Vector3(TeaStoveX, 0, TeaStoveZ); teaStove.localRotation = Quaternion.Euler(0, 180, 0);
            var tea = player.AddComponent<YunJing.Tea.TeaBrewingPanel>(); tea.stove = teaStove;
            stations.teaStove = tea;
            QingxiNoviceVillageBuilder.TrainingGlow(training);
            stations.training = training;
            foraging.abc = stations;
            walker.localForaging = foraging;
            var hud = new GameObject("Interior HUD").AddComponent<QingxiInteriorHud>();
            hud.place = "我的領地";
            hud.stations = stations; hud.training = training;
            var touch = player.AddComponent<QingxiTouchControls>(); touch.training = training;

            QingxiUrpUpgrade.UpgradeSceneMaterials();
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("QINGXI_LODGING_INTERIOR_GENERATED: " + ScenePath);
        }

        static void Shell(Transform room)
        {
            var floor = Surface("LodgingFloor_Placeholder", new Color(.42f, .30f, .20f));
            var wall = Surface("LodgingWall_Placeholder", new Color(.80f, .74f, .62f));
            var beam = Surface("LodgingBeam_Placeholder", new Color(.30f, .20f, .13f));
            Box(room, "Placeholder_Floor", new Vector3(0, -.05f, 0), new Vector3(W, .1f, D), floor);
            Box(room, "Placeholder_Ceiling", new Vector3(0, H + .05f, 0), new Vector3(W, .1f, D), beam);
            // Back wall with an open doorway to the backyard.
            float back = (W - 1.2f) / 2;
            Box(room, "Placeholder_WallBackLeft", new Vector3(-W / 2 + back / 2, H / 2, D / 2 + .05f), new Vector3(back, H, .1f), wall);
            Box(room, "Placeholder_WallBackRight", new Vector3(W / 2 - back / 2, H / 2, D / 2 + .05f), new Vector3(back, H, .1f), wall);
            Box(room, "Placeholder_WallBackTop", new Vector3(0, 2.2f + (H - 2.2f) / 2, D / 2 + .05f), new Vector3(1.2f, H - 2.2f, .1f), wall);
            Box(room, "Placeholder_WallLeft", new Vector3(-W / 2 - .05f, H / 2, 0), new Vector3(.1f, H, D), wall);
            Box(room, "Placeholder_WallRight", new Vector3(W / 2 + .05f, H / 2, 0), new Vector3(.1f, H, D), wall);
            // Front wall with the door opening (1.2 m wide, 2.2 m high); the opening is closed by a dark door panel.
            float side = (W - 1.2f) / 2;
            Box(room, "Placeholder_WallFrontLeft", new Vector3(-W / 2 + side / 2, H / 2, -D / 2 - .05f), new Vector3(side, H, .1f), wall);
            Box(room, "Placeholder_WallFrontRight", new Vector3(W / 2 - side / 2, H / 2, -D / 2 - .05f), new Vector3(side, H, .1f), wall);
            Box(room, "Placeholder_WallFrontTop", new Vector3(0, 2.2f + (H - 2.2f) / 2, -D / 2 - .05f), new Vector3(1.2f, H - 2.2f, .1f), wall);
            Box(room, "Placeholder_DoorPanel", new Vector3(0, 1.1f, -D / 2 - .1f), new Vector3(1.2f, 2.2f, .06f), beam);
            foreach (var x in new[] { -W / 2 + .15f, W / 2 - .15f })
                foreach (var z in new[] { -D / 2 + .15f, D / 2 - .15f })
                    Box(room, "Placeholder_Pillar", new Vector3(x, H / 2, z), new Vector3(.22f, H, .22f), beam);
            Box(room, "Placeholder_RoofBeam", new Vector3(0, H - .15f, 0), new Vector3(W, .2f, .25f), beam);
        }

        static void Lights(Transform room)
        {
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.55f, .5f, .44f);
            RenderSettings.ambientEquatorColor = new Color(.42f, .36f, .3f);
            RenderSettings.ambientGroundColor = new Color(.2f, .16f, .12f);
            RenderSettings.fog = false;
            var lamp = new GameObject("Lantern light").AddComponent<Light>();
            lamp.transform.SetParent(room, false); lamp.transform.localPosition = new Vector3(0, H - .5f, .3f);
            lamp.type = LightType.Point; lamp.range = 8; lamp.intensity = 2.2f; lamp.color = new Color(1f, .82f, .6f); lamp.shadows = LightShadows.Soft;
            var window = new GameObject("Window light").AddComponent<Light>();
            window.transform.SetParent(room, false); window.transform.rotation = Quaternion.Euler(40, 120, 0);
            window.type = LightType.Directional; window.intensity = .5f; window.color = new Color(.85f, .9f, 1f);
            // Daylight for the backyard; the roof keeps the room in shade.
            var sun = new GameObject("Yard sun").AddComponent<Light>();
            sun.transform.SetParent(room, false); sun.transform.rotation = Quaternion.Euler(48, -35, 0);
            sun.type = LightType.Directional; sun.intensity = 1.15f; sun.color = new Color(1f, .93f, .82f); sun.shadows = LightShadows.Soft;
            RenderSettings.skybox = QingxiNoviceVillageBuilder.Sky();
            // K11: the backyard sky follows the same clock as the village; the room keeps its lantern.
            var dayNight = new GameObject("Qingxi Day and Night (K11)").AddComponent<QingxiDayNight>();
            dayNight.sun = sun; dayNight.sky = RenderSettings.skybox;
        }

        // Walled backyard behind the house: two spirit fields, a stone path and the practice post.
        const float YardW = 12f, YardD = 10f;
        static void Yard(Transform room, out QingxiTerritoryFields fields, out Transform practicePost)
        {
            var yard = new GameObject("Territory_Backyard").transform; yard.SetParent(room, false);
            yard.localPosition = new Vector3(0, 0, D / 2);
            var soil = Surface("TerritoryYard_Ground", new Color(.46f, .52f, .32f));
            var stone = Surface("TerritoryYard_Path", new Color(.62f, .6f, .55f));
            var fence = Surface("TerritoryYard_Fence", new Color(.36f, .26f, .17f));
            var leaf = Surface("TerritoryYard_Sprout", new Color(.38f, .66f, .34f));
            Box(yard, "Yard_Ground", new Vector3(0, -.05f, YardD / 2), new Vector3(YardW, .1f, YardD), soil);
            Box(yard, "Yard_Path", new Vector3(0, .01f, YardD / 2), new Vector3(1.1f, .04f, YardD - .4f), stone);
            const float F = 1.1f;
            Box(yard, "Yard_FenceBack", new Vector3(0, F / 2, YardD), new Vector3(YardW, F, .12f), fence);
            Box(yard, "Yard_FenceLeft", new Vector3(-YardW / 2, F / 2, YardD / 2), new Vector3(.12f, F, YardD), fence);
            Box(yard, "Yard_FenceRight", new Vector3(YardW / 2, F / 2, YardD / 2), new Vector3(.12f, F, YardD), fence);
            // The yard is wider than the house: close the gaps between the house and the side fences.
            Box(yard, "Yard_FenceFrontLeft", new Vector3(-(YardW + W) / 4, F / 2, 0), new Vector3((YardW - W) / 2, F, .12f), fence);
            Box(yard, "Yard_FenceFrontRight", new Vector3((YardW + W) / 4, F / 2, 0), new Vector3((YardW - W) / 2, F, .12f), fence);
            // A taller invisible rim so nobody climbs out over the low fence.
            foreach (var (n, at, size) in new[] {
                ("Yard_Rim_Back", new Vector3(0, 2, YardD + .2f), new Vector3(YardW + 1, 4, .2f)),
                ("Yard_Rim_Left", new Vector3(-YardW / 2 - .2f, 2, YardD / 2), new Vector3(.2f, 4, YardD + 1)),
                ("Yard_Rim_Right", new Vector3(YardW / 2 + .2f, 2, YardD / 2), new Vector3(.2f, 4, YardD + 1)),
                ("Yard_Rim_FrontLeft", new Vector3(-(YardW + W) / 4, 2, -.2f), new Vector3((YardW - W) / 2, 4, .2f)),
                ("Yard_Rim_FrontRight", new Vector3((YardW + W) / 4, 2, -.2f), new Vector3((YardW - W) / 2, 4, .2f)) })
            {
                var rim = new GameObject(n).AddComponent<BoxCollider>(); rim.transform.SetParent(yard, false);
                rim.transform.localPosition = at; rim.size = size;
            }

            fields = room.gameObject.AddComponent<QingxiTerritoryFields>();
            var list = new System.Collections.Generic.List<QingxiTerritoryFields.Field>();
            foreach (var x in new[] { -2.8f, 2.8f })
            {
                var bed = EstateModel("spirit-bed", "SpiritField_" + (list.Count + 1), yard, new Vector3(x, 0, 4.2f));
                var crop = new GameObject("Crop").transform; crop.SetParent(yard, false);
                crop.position = bed.transform.position + Vector3.up * .3f;
                for (int r = 0; r < 4; r++)
                    for (int c = 0; c < 3; c++)
                    {
                        var sprout = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                        UnityEngine.Object.DestroyImmediate(sprout.GetComponent<Collider>());
                        sprout.name = "Sprout"; sprout.transform.SetParent(crop, false);
                        sprout.transform.localPosition = new Vector3((c - 1) * .6f, .22f, (r - 1.5f) * .62f);
                        sprout.transform.localScale = new Vector3(.16f, .22f, .16f);
                        sprout.GetComponent<Renderer>().sharedMaterial = leaf;
                    }
                var glow = new GameObject("RipeGlow").AddComponent<Light>(); glow.transform.SetParent(crop, false);
                glow.transform.localPosition = new Vector3(0, .8f, 0);
                glow.type = LightType.Point; glow.range = 3.2f; glow.intensity = 1.4f; glow.color = new Color(1f, .86f, .45f);
                glow.gameObject.SetActive(false);
                list.Add(new QingxiTerritoryFields.Field { bed = bed.transform, crop = crop });
            }
            fields.fields = list.ToArray();

            var result = new QingxiCollaboratorZonesBuilder.Result();
            practicePost = QingxiCollaboratorZonesBuilder.PlaceTrainingProp("agility-post", yard, new Vector3(0, 0, 8.3f), 180, result).transform;
        }

        // The 10/31 work packs' slots (docs/execution/2026-10-31/01-A, 02-B): outline frames with labels until the
        // collaborators' models arrive. Scene coordinates; footprint is width × depth × height in metres.
        static readonly (string id, string role, string owner, float x, float z, float yaw, float w, float d, float h)[] Slots =
        {
            ("TY_Field_1", "領地靈田（TY01）", "Johnnnny0823", -2.8f, 6.7f, 0, 2.6f, 3.4f, .5f),
            ("TY_Field_2", "領地靈田（TY01）", "Johnnnny0823", 2.8f, 6.7f, 0, 2.6f, 3.4f, .5f),
            ("TY_Practice", "練功地面（TY05）", "Johnnnny0823", 0, 10.8f, 0, 3.2f, 3.2f, .15f),
            ("TY_Lantern", "院角舊石燈・守燈（TY04）", "Johnnnny0823", -5.2f, 12f, 0, .9f, .9f, 2f),
            ("TY_Corner_R", "生活雜物組（TY09）", "Johnnnny0823", 5f, 11.5f, 0, 1.6f, 1.6f, 2f),
            ("TY_Rack", "晾藥架（TY08）", "Johnnnny0823", 5.4f, 4f, 0, .8f, 2f, 1.8f),
            ("TI_Shelf", "收藏架・博古架（TI01）", "joshsu54", 3.25f, -.6f, -90, 1.8f, .45f, 2f),
            ("TI_Desk", "書案與椅凳（TI03）", "joshsu54", -2.6f, -1.6f, 90, 1.3f, .7f, .85f),
            ("TI_Furnace", "小丹爐（TI02）", "joshsu54", 2.7f, -1.9f, -90, .8f, .8f, 1.1f),
            ("TI_Lamp_1", "燈架（TI04）", "joshsu54", -1.6f, 2.1f, 0, .45f, .45f, 1.7f),
            ("TI_Lamp_2", "燈架（TI04）", "joshsu54", 1.9f, -2.1f, 0, .45f, .45f, 1.7f),
            ("TI_Screen", "屏風（TI05）", "joshsu54", -1.4f, .4f, 0, 1.8f, .35f, 1.75f),
            ("TI_Rug", "地蓆（TI06）", "joshsu54", .6f, 0, 0, 2f, 1.4f, .03f),
            ("TI_TeaStove", "家用茶爐（TI09・泡茶）", "joshsu54", TeaStoveX, TeaStoveZ, 180, .7f, .7f, .9f),
        };

        static void TerritorySlots(Transform room)
        {
            var root = new GameObject("Territory_PlannedSlots").transform; root.SetParent(room, false);
            foreach (var s in Slots)
            {
                var p = new QingxiVillageTerrain.Placement { id = s.id, role = s.role, owner = s.owner, status = "needed", yaw = s.yaw, footprint = new[] { s.w, s.d, s.h } };
                QingxiNoviceVillageBuilder.PlannedSlot(root, p, new Vector3(s.x, 0, s.z));
            }
        }

        static GameObject EstateModel(string key, string name, Transform parent, Vector3 at)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/YunJing/Models/IrrigationV2/{key}.fbx");
            if (source == null) throw new FileNotFoundException("Spirit field model missing", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = name + " - core (IrrigationV2)";
            model.transform.SetParent(parent, false);
            model.transform.localPosition = at;
            return model;
        }

        static GameObject Furniture(string folder, string key, Transform room, Vector3 at, float yaw)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"{Models}/{key}.fbx");
            if (source == null) throw new FileNotFoundException("Interior furniture missing (Git LFS pulled?)", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = key + " - joshsu54 (dondon)";
            model.transform.SetParent(room, false);
            model.transform.localRotation = Quaternion.Euler(0, yaw, 0) * source.transform.localRotation;
            model.transform.localPosition = at;
            var rs = model.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            model.transform.position += Vector3.up * (room.position.y + at.y - b.min.y);
            b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            var box = model.AddComponent<BoxCollider>();
            box.center = model.transform.InverseTransformPoint(b.center);
            var size = model.transform.InverseTransformVector(b.size);
            box.size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
            return model;
        }

        static void CopyFurniture()
        {
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            string target = Path.Combine(repo, "apps/game", Models);
            Directory.CreateDirectory(target);
            foreach (var (folder, version) in new[] { ("DiscipleBed", "v001"), ("StorageChest", "v001"), ("MeditationCushion", "v001") })
            {
                var src = Path.Combine(repo, "art/incoming/dondon", folder, version);
                foreach (var file in Directory.GetFiles(src, "*.fbx"))
                {
                    if (new FileInfo(file).Length < 1024) throw new InvalidOperationException("Git LFS pointer instead of asset; run git lfs pull: " + file);
                    var to = Path.Combine(target, Path.GetFileName(file));
                    if (!File.Exists(to) || new FileInfo(to).Length != new FileInfo(file).Length) File.Copy(file, to, true);
                }
            }
            AssetDatabase.Refresh();
        }

        static void Box(Transform parent, string name, Vector3 at, Vector3 size, Material material)
        {
            var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = name; box.transform.SetParent(parent, false);
            box.transform.localPosition = at; box.transform.localScale = size;
            box.GetComponent<Renderer>().sharedMaterial = material;
        }

        static Material Surface(string name, Color color)
        {
            var path = $"{MaterialFolder}/{name}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", color); mat.SetFloat("_Smoothness", .1f);
            EditorUtility.SetDirty(mat);
            return mat;
        }
    }
}
