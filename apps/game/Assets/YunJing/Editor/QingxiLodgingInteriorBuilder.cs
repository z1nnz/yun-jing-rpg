using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace YunJing.Editor
{
    // The newcomer's own territory (K23): a pocket world of its own (docs/execution/territory-small-world-plan.md),
    // entered through the Qingxi lodging door with a fade. A 60 × 60 m hollow from tools/qingxi-terrain/territory.json,
    // built with the same terrain, slot and dressing code as the big world: the old house (joshsu54's StarterHouse)
    // in the middle, two spirit fields (QingxiTerritoryFields, planted and harvested through the server), the
    // practice ground with Johnnnny0823's agility post, the corner and pavilion slots, a spring in the north, and a
    // ring of gentle hills in mist. The house door leads into the room (joshsu54's bed, chest and cushion, B's
    // 10/31 interior slots), which stands apart from the hollow; the wicker gate goes back out to the big world.
    public static class QingxiLodgingInteriorBuilder
    {
        public const string ScenePath = "Assets/YunJing/Generated/QingxiLodgingInterior.unity";
        const string Models = "Assets/YunJing/Models/LodgingInterior";   // copied from art/incoming/dondon, gitignored
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/Collaborators";
        const float W = 7f, D = 5f, H = 3.2f;   // room width (x), depth (z), height
        static readonly Vector3 RoomAt = new Vector3(0, 0, -120);   // the room stands outside the hollow, behind the mist

        public static void Generate()
        {
            QingxiUrpUpgrade.EnsurePipeline();
            CopyFurniture();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var world = new GameObject("QingxiTerritory").transform;
            var layout = QingxiVillageTerrain.Load("tools/qingxi-terrain/territory.json");
            var terrain = QingxiVillageTerrain.Create(world, layout, "TerritoryTerrain", "TerritoryTerrain (territory.json)");
            QingxiNoviceVillageBuilder.BuildBlock(world, layout, terrain, "TR");
            Vector3 Ground(float x, float z) => new Vector3(x, QingxiVillageTerrain.Ground(terrain, x, z), z);
            Vector2 Node(string id) { var n = layout.nodes.First(k => k.id == id); return new Vector2(n.x, n.z); }
            Vector2 Slot(string id) { var p = layout.placements.First(k => k.id == id); return new Vector2(p.x, p.z); }

            var room = new GameObject("QingxiLodgingInterior (the room)").transform;
            room.SetParent(world, false); room.localPosition = RoomAt;
            Shell(room);
            Lights(world, room);
            Rim(world, layout);
            var fields = Fields(world, new[] { Slot("TY_Field_1"), Slot("TY_Field_2") }, Ground);
            var practice = Slot("TY_Practice");
            var result = new QingxiCollaboratorZonesBuilder.Result();
            var practicePost = QingxiCollaboratorZonesBuilder.PlaceTrainingProp("agility-post", world, Ground(practice.x, practice.y), 180, result).transform;
            TerritorySlots(room);

            var bed = Furniture("DiscipleBed", "DiscipleBed_v001", room, new Vector3(-W / 2 + .75f, 0, 1.0f), 90f);
            var chest = Furniture("StorageChest", "StorageChest_v001", room, new Vector3(W / 2 - .9f, 0, D / 2 - .6f), 180f);
            var cushion = Furniture("MeditationCushion", "MeditationCushion_v001", room, new Vector3(1.2f, 0, -.2f), 0f);

            // Doors. Each faces the way the player walks out of it, so arriving through one leaves the player
            // looking away from it: the gate and the house door face south (out), the room door faces into the room.
            var gateAt = Node("tr-gate");
            var gate = new GameObject("ExitGate_Territory").transform; gate.SetParent(world, false);
            gate.position = Ground(gateAt.x, gateAt.y); gate.rotation = Quaternion.Euler(0, 180, 0);
            var doorAt = Node("tr-door");
            var houseDoor = new GameObject("HouseDoor_Territory").transform; houseDoor.SetParent(world, false);
            houseDoor.position = Ground(doorAt.x, doorAt.y); houseDoor.rotation = Quaternion.Euler(0, 180, 0);
            var roomDoor = new GameObject("RoomDoor_Lodging").transform; roomDoor.SetParent(room, false);
            roomDoor.localPosition = new Vector3(0, 0, -D / 2 + .7f);

            // Arrive just inside the gate, looking up the path to the house.
            var spawn = Ground(gateAt.x, gateAt.y + 2.5f) + Vector3.up * .05f;
            var player = QingxiNoviceVillageBuilder.Player(world, spawn);
            var walker = player.GetComponent<global::QingxiWorld.QingxiFirstPerson>();
            walker.useDesignedHud = true;
            walker.spotNames = new[] { "我的領地", "屋裡" };
            walker.spotPositions = new[] { spawn, room.TransformPoint(new Vector3(0, .05f, -D / 2 + 1.2f)) };
            walker.spotYaws = new[] { 0f, 0f };
            walker.pointsOfInterest = new Transform[0];
            var foraging = player.AddComponent<QingxiLocalForaging>();
            foraging.herbNodes = new Transform[0]; foraging.clueNodes = new Transform[0];
            var stations = player.AddComponent<QingxiAbcStations>();
            stations.exitDoor = gate; stations.houseDoor = houseDoor; stations.roomDoor = roomDoor;
            stations.bed = bed.transform; stations.chest = chest.transform; stations.walker = walker;
            var training = player.AddComponent<QingxiTrainingPractice>();
            training.qiPost = cushion.transform; training.qiLabel = "蒲團"; training.walker = walker;
            training.blockPost = practicePost;
            stations.fields = fields;
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
            Box(room, "Placeholder_WallBack", new Vector3(0, H / 2, D / 2 + .05f), new Vector3(W, H, .1f), wall);
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

        static void Lights(Transform world, Transform room)
        {
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.58f, .62f, .66f);
            RenderSettings.ambientEquatorColor = new Color(.46f, .47f, .42f);
            RenderSettings.ambientGroundColor = new Color(.22f, .2f, .16f);
            // Mist: the hills at the rim soften into it and the hollow reads as a world of its own.
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogStartDistance = 22; RenderSettings.fogEndDistance = 75;
            RenderSettings.fogColor = new Color(.80f, .84f, .84f);
            var lamp = new GameObject("Lantern light").AddComponent<Light>();
            lamp.transform.SetParent(room, false); lamp.transform.localPosition = new Vector3(0, H - .5f, .3f);
            lamp.type = LightType.Point; lamp.range = 8; lamp.intensity = 2.2f; lamp.color = new Color(1f, .82f, .6f); lamp.shadows = LightShadows.Soft;
            var sun = new GameObject("Territory sun").AddComponent<Light>();
            sun.transform.SetParent(world, false); sun.transform.rotation = Quaternion.Euler(48, -35, 0);
            sun.type = LightType.Directional; sun.intensity = 1.35f; sun.color = new Color(1f, .9f, .74f); sun.shadows = LightShadows.Soft;
            RenderSettings.sun = sun;
            RenderSettings.skybox = QingxiNoviceVillageBuilder.Sky();
            // K11: the hollow's sky follows the same clock as the village; the room keeps its lantern.
            QingxiNoviceVillageBuilder.PostCard(world);   // the same golden grade as the big world
            var dayNight = new GameObject("Qingxi Day and Night (K11)").AddComponent<QingxiDayNight>();
            dayNight.sun = sun; dayNight.sky = RenderSettings.skybox;
            dayNight.fogScale = .6f;   // the clock drives the fog at run time; keep it close so the rim stays misty
        }

        // Invisible walls on the hill slopes, 4 m inside the edge: the hills and the mist beyond are scenery.
        static void Rim(Transform world, QingxiVillageTerrain.Layout layout)
        {
            var a = layout.bounds; float inset = 4, tall = 40;
            float x0 = a.minX + inset, x1 = a.minX + a.sizeX - inset, z0 = a.minZ + inset, z1 = a.minZ + a.sizeZ - inset;
            foreach (var (n, at, size) in new[] {
                ("Rim_North", new Vector3((x0 + x1) / 2, tall / 2, z1), new Vector3(x1 - x0, tall, .4f)),
                ("Rim_South", new Vector3((x0 + x1) / 2, tall / 2, z0), new Vector3(x1 - x0, tall, .4f)),
                ("Rim_West", new Vector3(x0, tall / 2, (z0 + z1) / 2), new Vector3(.4f, tall, z1 - z0)),
                ("Rim_East", new Vector3(x1, tall / 2, (z0 + z1) / 2), new Vector3(.4f, tall, z1 - z0)) })
            {
                var rim = new GameObject(n).AddComponent<BoxCollider>(); rim.transform.SetParent(world, false);
                rim.transform.localPosition = at; rim.size = size;
            }
        }

        // The two spirit fields on their slots (TY_Field_1, TY_Field_2), each with a crop and a ripe glow.
        static QingxiTerritoryFields Fields(Transform world, Vector2[] at, Func<float, float, Vector3> ground)
        {
            var leaf = Surface("TerritoryYard_Sprout", new Color(.38f, .66f, .34f));
            var fields = world.gameObject.AddComponent<QingxiTerritoryFields>();
            var list = new System.Collections.Generic.List<QingxiTerritoryFields.Field>();
            foreach (var p in at)
            {
                var bed = EstateModel("spirit-bed", "SpiritField_" + (list.Count + 1), world, ground(p.x, p.y));
                var crop = new GameObject("Crop").transform; crop.SetParent(world, false);
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
            return fields;
        }

        // B's 10/31 interior slots (docs/execution/2026-10-31/02-B) as outline frames until the models arrive, plus
        // the tea stove (not yet assigned). Room coordinates; footprint is width × depth × height in metres. The
        // yard slots come from territory.json.
        static readonly (string id, string role, string owner, float x, float z, float yaw, float w, float d, float h)[] Slots =
        {
            ("TI_Shelf", "收藏架・博古架（TI01）", "joshsu54", 3.25f, -.6f, -90, 1.8f, .45f, 2f),
            ("TI_Desk", "書案與椅凳（TI03）", "joshsu54", -2.6f, -1.6f, 90, 1.3f, .7f, .85f),
            ("TI_Furnace", "小丹爐（TI02）", "joshsu54", 2.7f, -1.9f, -90, .8f, .8f, 1.1f),
            ("TI_Lamp_1", "燈架（TI04）", "joshsu54", -1.6f, 2.1f, 0, .45f, .45f, 1.7f),
            ("TI_Lamp_2", "燈架（TI04）", "joshsu54", 1.9f, -2.1f, 0, .45f, .45f, 1.7f),
            ("TI_Screen", "屏風（TI05）", "joshsu54", -1.4f, .4f, 0, 1.8f, .35f, 1.75f),
            ("TI_Rug", "地蓆（TI06）", "joshsu54", .6f, 0, 0, 2f, 1.4f, .03f),
            ("TI_TeaStove", "茶爐（茶亭老人教過以後）", "core", -.2f, 2.0f, 180, .7f, .7f, .9f),
        };

        static void TerritorySlots(Transform room)
        {
            var root = new GameObject("Territory_PlannedSlots").transform; root.SetParent(room, false);
            foreach (var s in Slots)
            {
                var p = new QingxiVillageTerrain.Placement { id = s.id, role = s.role, owner = s.owner, status = "needed", yaw = s.yaw, footprint = new[] { s.w, s.d, s.h } };
                QingxiNoviceVillageBuilder.PlannedSlot(root, p, room.position + new Vector3(s.x, 0, s.z));
            }
        }

        static GameObject EstateModel(string key, string name, Transform parent, Vector3 at)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/YunJing/Models/IrrigationV2/{key}.fbx");
            if (source == null) throw new FileNotFoundException("Spirit field model missing", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = name + " - core (IrrigationV2)";
            model.transform.SetParent(parent, false);
            model.transform.position = at;
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
