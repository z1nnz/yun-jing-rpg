using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace YunJing.Editor
{
    // A small novice village for reviewing the collaborators' complete deliveries without the
    // larger world's terrain, trees and buildings in the way:
    //   south  village gate (spawn)          centre  plaza, Eli-0731's notice board and return corner (C)
    //   west   joshsu54's alchemy corner (B), door into his AlchemyRoom scene
    //   east   Johnnnny0823's training yard  north   Johnnnny0823's forest rabbit encounter (A)
    // The ground is a continuous terrain from tools/qingxi-terrain/novice-village.json (QingxiVillageTerrain);
    // every zone stands on a flat pad and everything else is dropped onto the terrain height.
    // The herb markers are graybox placeholders and are named so.
    public static class QingxiNoviceVillageBuilder
    {
        public const string ScenePath = "Assets/YunJing/Generated/QingxiNoviceVillage.unity";
        const string AlchemyScenePath = "Assets/YunJing/Generated/AlchemyRoom.unity";
        const string MaterialFolder = "Assets/QingxiWorld/Generated/Materials/Collaborators";
        static Terrain terrain;
        static QingxiVillageTerrain.Layout layout;
        const string GatheringModels = "Assets/YunJing/Models/GatheringB";   // copied from art/exports, gitignored

        static Vector3 At(float x, float z) => new Vector3(x, QingxiVillageTerrain.Ground(terrain, x, z), z);
        static Vector3 At(Vector3 p) => At(p.x, p.z);

        [MenuItem("Yun Jing/Generate Qingxi novice village")]
        public static void Generate()
        {
            QingxiUrpUpgrade.EnsurePipeline();
            // All village input (walker, encounter, drills, HUD, touch) uses the Input System package. With the
            // legacy-only handler (0) Keyboard.current and Mouse.current are null and nothing responds, in the
            // Windows player and the browser alike. Takes effect from the next Editor process (the build step).
            var settings = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            settings.FindProperty("activeInputHandler").intValue = 1; settings.ApplyModifiedPropertiesWithoutUndo();
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(MaterialFolder);
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var village = new GameObject("QingxiNoviceVillage").transform;
            Lighting(village);
            terrain = QingxiVillageTerrain.Create(village);
            layout = QingxiVillageTerrain.Load();
            Physics.SyncTransforms();
            Boundary(village);

            var player = Player(village, At(0, -22));
            var zones = QingxiCollaboratorZonesBuilder.PlaceAt(player,
                At(0, 24), 0,                                     // A: shelter (local -z) faces the plaza
                At(-15, -2), Facing(new Vector3(-15, 0, -2), Vector3.zero),
                // C: north-east of the plaza, clear of the road to the training yard (z = -2).
                At(5.5f, 2.2f), Facing(new Vector3(5.5f, 0, 2.2f), Vector3.zero));
            foreach (var zone in new[] { zones.forest, zones.alchemy, zones.ret }) zone.SetParent(village, true);

            var yard = TrainingYard(village, zones);
            var signs = Signs(village, zones);
            var herbs = Herbs(village);
            var placed = Placements(village);
            Creek(village);
            Scenery(village);
            // The creek chapter in the village: joshsu54's old channel (PR #52) and Eli-0731's council corner (PR #47).
            var works = QingxiWaterworksB.Build(village);
            var council = layout.placements.First(p => p.id == "Plaza_WaterCouncil");
            var report = new GameObject("WaterCouncil (village-report)").AddComponent<QingxiVillageReport>();
            report.transform.SetParent(village, false);
            report.point = new GameObject("Council talk point").transform;
            report.point.SetParent(report.transform, false);
            report.point.position = At(council.x, council.z);

            var walker = player.GetComponent<global::QingxiWorld.QingxiFirstPerson>();
            var spots = new (string name, Vector3 at, Vector3 look)[] {
                ("村口", At(0, -22), Vector3.zero),
                ("小廣場", At(0, -6), new Vector3(0, 0, 10)),
                ("溪畔丹房", zones.alchemyDoor.position, zones.alchemy.position),
                ("演武區", yard.position + new Vector3(-4, 0, 0), yard.position),
                ("林地遭遇", zones.forest.Find("SafePoint_A09").position, zones.forest.Find("RabbitBurrow_A02").position),
                ("回村分揀桌", zones.returnTable.position, zones.ret.position),
                ("坊市", At(-6, -14), At(-11, -15)),
                ("藥田", At(-18, -21), At(-25, -24)),
                ("舊水路", works.point.position, works.point.position + new Vector3(1.2f, 0, 0)),
                ("議水桌", report.point.position + new Vector3(0, 0, -2.5f), report.point.position),
            };
            walker.spotNames = spots.Select(s => s.name).ToArray();
            walker.spotPositions = spots.Select(s => s.at).ToArray();
            walker.spotYaws = spots.Select(s => Mathf.Atan2(s.look.x - s.at.x, s.look.z - s.at.z) * Mathf.Rad2Deg).ToArray();
            walker.pointsOfInterest = signs.Concat(herbs).Concat(new[] { yard, zones.alchemyDoor, zones.returnTable }).ToArray();

            var hud = new GameObject("Qingxi Designed HUD").AddComponent<QingxiHud>();
            hud.walker = walker;
            hud.uiMaterial = UiMaterial();
            var foraging = player.AddComponent<QingxiLocalForaging>();
            foraging.herbNodes = herbs;
            foraging.clueNodes = signs.Skip(1).ToArray();   // Q02-Q04 are Eli-0731's clue signs; Q01 is the notice board
            foraging.trainingSpot = shelterSpot;
            // The herbal stall is the market: herbs and rabbits trade for practice stones there (local only).
            var market = new GameObject("MarketEntrance_HerbalStall").transform;
            market.SetParent(village, false); market.position = At(-7.5f, -14.5f);
            foraging.marketEntrance = market;
            foreach (var visual in herbs.Select(h => h.GetComponent<QingxiHerbVisual>()).Where(v => v != null)) visual.foraging = foraging;
            var stations = player.AddComponent<QingxiAbcStations>();
            stations.alchemyDoor = zones.alchemyDoor; stations.returnTable = zones.returnTable;
            stations.forest = zones.encounter; stations.walker = walker;
            var training = player.AddComponent<QingxiTrainingPractice>();
            training.qiPost = qiPost; training.blockPost = blockPost; training.walker = walker;
            TrainingGlow(training);
            stations.training = training;
            var fortunes = player.AddComponent<QingxiFortunes>();
            fortunes.glowDot = training.glowDot;
            fortunes.fortunes = (layout.fortunes ?? new QingxiVillageTerrain.FortuneSpot[0]).Select(f => new QingxiFortunes.Fortune {
                id = f.id, title = f.title, passage = f.passage, reward = f.reward, position = At(f.x, f.z), nightOnly = f.condition == "night" }).ToArray();
            stations.fortunes = fortunes;
            DayNight(village, zones.alchemyDoor.position, qiPost.position);
            // The lodging's front door (west side, facing the road) leads into its interior scene.
            var lodgingDoor = new GameObject("LodgingDoor_StarterHouse").transform;
            lodgingDoor.SetParent(village, false); lodgingDoor.position = At(11.8f, -19.5f); lodgingDoor.rotation = Quaternion.Euler(0, 90, 0);
            stations.lodgingDoor = lodgingDoor;
            var touch = player.AddComponent<QingxiTouchControls>();
            touch.forest = zones.encounter; touch.training = training; touch.foraging = foraging;
            var trainingParity = QingxiTrainingPracticeSmoke.Verify();
            foraging.abc = stations;
            walker.localForaging = foraging;
            hud.foraging = foraging; hud.forest = zones.encounter; hud.stations = stations;
            new GameObject("Qingxi ABC build smoke (--abc-smoke)").AddComponent<QingxiAbcSmoke>();
            new GameObject("Qingxi Server Link (K7)").AddComponent<QingxiServerLink>();   // online when the game server runs, offline otherwise
            var streamer = new GameObject("Qingxi Block Streamer (K5)").AddComponent<QingxiBlockStreamer>();
            streamer.gameObject.AddComponent<QingxiUpstreamShots>();   // --upstream-shots: review views of D3
            streamer.blocks = QingxiBlockBuilder.Blocks.Select(b =>
            {
                var a = QingxiVillageTerrain.Load($"tools/qingxi-terrain/blocks/{b.id}.json").bounds;
                return new QingxiBlockStreamer.Block { id = b.id, scene = "QingxiBlock_" + b.id, area = new Rect(a.minX, a.minZ, a.sizeX, a.sizeZ) };
            }).ToArray();

            var converted = QingxiUrpUpgrade.UpgradeSceneMaterials();
            var swaying = WindFoliage(village);
            Debug.Log("QINGXI_WIND: " + swaying + " foliage renderers sway");
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.defaultScreenWidth = 1280;
            PlayerSettings.defaultScreenHeight = 720;
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log($"QINGXI_NOVICE_VILLAGE_GENERATED: collaborator models={zones.models}, placements={placed}, spots={spots.Length}, herbs={herbs.Length}, clues={foraging.clueNodes.Length}, URP copies={converted}, {trainingParity}\n" + string.Join("\n", zones.report));
            PrepareAlchemyRoom();
            QingxiLodgingInteriorBuilder.Generate();
            QingxiBlockBuilder.GenerateAll();
        }

        static string[] Scenes => new[] { ScenePath, AlchemyScenePath, QingxiLodgingInteriorBuilder.ScenePath }
            .Concat(QingxiBlockBuilder.Blocks.Select(b => QingxiBlockBuilder.ScenePath(b.id))).ToArray();

        static float Facing(Vector3 from, Vector3 target)
        {
            var toward = target - from;   // the zone's local -z (entrance side) points at the target
            return Mathf.Atan2(-toward.x, -toward.z) * Mathf.Rad2Deg;
        }

        // ------------------------------------------------------------------ ground, light, player
        static void Lighting(Transform village)
        {
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.transform.SetParent(village, false);
            sun.type = LightType.Directional; sun.intensity = 1.15f; sun.shadows = LightShadows.Soft; sun.color = new Color(1f, .95f, .86f);
            sun.transform.rotation = Quaternion.Euler(48, -35, 0);
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.62f, .7f, .78f); RenderSettings.ambientEquatorColor = new Color(.55f, .58f, .52f); RenderSettings.ambientGroundColor = new Color(.32f, .3f, .26f);
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear; RenderSettings.fogColor = new Color(.78f, .83f, .84f);
            RenderSettings.fogStartDistance = 45; RenderSettings.fogEndDistance = 120;
            RenderSettings.skybox = Sky();
            PostCard(village);
        }

        // K11: the day follows the real clock (QingxiDayNight). Night lights stand where people live and work:
        // the gate lanterns (Codex C7 brings the stone lanterns), the lodging door, the market, the smithy's forge,
        // the shops, the homes, the alchemy door and the training yard; and the "third lantern" of find A1-F08,
        // which only ever shows at night. Point lights without shadows, a dozen at most, for phones.
        static void DayNight(Transform village, Vector3 alchemyDoor, Vector3 trainingPost)
        {
            var root = new GameObject("Night Lights (K11)").transform; root.SetParent(village, false);
            var warm = new Color(1f, .7f, .4f);
            var lights = new List<Light>(); var glows = new List<Renderer>();
            void Lamp(string name, Vector3 ground, float height, float intensity, float range, Color colour, bool glow = true)
            {
                var light = new GameObject("NightLight " + name).AddComponent<Light>();
                light.transform.SetParent(root, false); light.transform.position = ground + Vector3.up * height;
                light.type = LightType.Point; light.range = range * 1.35f; light.intensity = intensity * 1.6f; light.color = colour;
                light.shadows = LightShadows.None; light.renderMode = LightRenderMode.Auto;
                lights.Add(light);
                if (!glow) return;
                var dot = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                dot.name = "NightGlow " + name; dot.transform.SetParent(light.transform, false); dot.transform.localScale = Vector3.one * .22f;
                UnityEngine.Object.DestroyImmediate(dot.GetComponent<Collider>());
                var r = dot.GetComponent<Renderer>(); r.sharedMaterial = NightGlowMaterial(colour); r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                glows.Add(r);
            }
            Vector3 Front(string id, float extra)
            {
                var p = layout.placements.FirstOrDefault(x => x.id == id);
                if (p == null) return Vector3.zero;
                float depth = p.footprint != null ? p.footprint[1] / 2 : 1;
                var forward = Quaternion.Euler(0, p.yaw, 0) * Vector3.forward;
                return At(new Vector3(p.x, 0, p.z) + forward * (depth + extra));
            }
            foreach (var id in new[] { "Gate_Lantern_L", "Gate_Lantern_R" })
            {
                var p = layout.placements.FirstOrDefault(x => x.id == id);
                if (p != null) Lamp(id, At(p.x, p.z), 1.9f, 2.4f, 8, warm);
            }
            Lamp("LodgingDoor", At(11.8f, -19.5f), 2.4f, 1.8f, 6, warm);
            Lamp("Market", Front("Market_HerbalStall", .8f), 2.3f, 1.8f, 7, warm);
            Lamp("SmithyForge", Front("Smithy_Blacksmith", .6f), 1.2f, 2.6f, 7, new Color(1f, .5f, .22f), glow: false);
            Lamp("MaterialShop", Front("Shops_MaterialShop", .6f), 2.4f, 1.6f, 6, warm);
            Lamp("Teahouse", Front("Shops_Teahouse", .4f), 2.3f, 1.6f, 6, warm);
            Lamp("Homes", At(25, 13), 2.4f, 1.6f, 8, warm);
            Lamp("PlazaNotice", Front("Plaza_NoticeBoard", .8f), 2.6f, 1.5f, 7, warm);
            Lamp("AlchemyDoor", alchemyDoor, 2.3f, 1.6f, 6, warm);
            Lamp("TrainingYard", trainingPost + new Vector3(2.2f, 0, 0), 2.6f, 1.4f, 7, warm);
            // The third lantern: a cooler, quieter light just past the gate, where find A1-F08 waits.
            var third = layout.fortunes?.FirstOrDefault(f => f.condition == "night");
            if (third != null) Lamp("ThirdLantern", At(third.x, third.z), 1.6f, 1.2f, 5, new Color(.85f, .92f, 1f));
            var dayNight = new GameObject("Qingxi Day and Night (K11)").AddComponent<QingxiDayNight>();
            dayNight.sun = RenderSettings.sun; dayNight.sky = RenderSettings.skybox;
            dayNight.nightLights = lights.ToArray(); dayNight.nightGlows = glows.ToArray();
        }

        static Material NightGlowMaterial(Color colour)
        {
            var path = $"{MaterialFolder}/NightGlow_{ColorUtility.ToHtmlStringRGB(colour)}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", Color.black); mat.SetColor("_EmissionColor", colour * 3.2f); mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Morning sky: a procedural skybox tinted to the haze, so the horizon melts into the fog instead of
        // ending at a grey void.
        internal static Material Sky()
        {
            var path = MaterialFolder + "/QingxiSky_Procedural.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Skybox/Procedural")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetFloat("_SunSize", .035f); mat.SetFloat("_SunSizeConvergence", 6);
            mat.SetFloat("_AtmosphereThickness", .85f); mat.SetFloat("_Exposure", 1.2f);
            mat.SetColor("_SkyTint", new Color(.5f, .62f, .74f)); mat.SetColor("_GroundColor", new Color(.66f, .72f, .7f));
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // The "postcard" grade for the novice village (P1): film tone mapping, a warm morning white balance,
        // a little more contrast and colour, soft bloom on bright sky and water, and a light vignette.
        // Cheap enough for phones: no depth of field, no SSAO.
        public static void PostCard(Transform parent)
        {
            var path = MaterialFolder + "/QingxiPostCard_Volume.asset";
            var profile = AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.VolumeProfile>(path);
            if (profile == null) { profile = ScriptableObject.CreateInstance<UnityEngine.Rendering.VolumeProfile>(); AssetDatabase.CreateAsset(profile, path); }
            T Get<T>() where T : UnityEngine.Rendering.VolumeComponent
            {
                if (!profile.TryGet<T>(out var c)) { c = profile.Add<T>(true); AssetDatabase.AddObjectToAsset(c, profile); }
                c.active = true;
                return c;
            }
            var tone = Get<UnityEngine.Rendering.Universal.Tonemapping>(); tone.mode.Override(UnityEngine.Rendering.Universal.TonemappingMode.ACES);
            var colour = Get<UnityEngine.Rendering.Universal.ColorAdjustments>();
            colour.postExposure.Override(.25f); colour.contrast.Override(12); colour.saturation.Override(10);
            var white = Get<UnityEngine.Rendering.Universal.WhiteBalance>(); white.temperature.Override(8); white.tint.Override(-3);
            var bloom = Get<UnityEngine.Rendering.Universal.Bloom>();
            bloom.threshold.Override(1.05f); bloom.intensity.Override(.35f); bloom.scatter.Override(.7f); bloom.highQualityFiltering.Override(false);
            var vignette = Get<UnityEngine.Rendering.Universal.Vignette>(); vignette.intensity.Override(.2f); vignette.smoothness.Override(.45f);
            EditorUtility.SetDirty(profile);
            var volume = new GameObject("PostCard Volume").AddComponent<UnityEngine.Rendering.Volume>();
            volume.transform.SetParent(parent, false);
            volume.isGlobal = true; volume.sharedProfile = profile;
        }

        // Keep the traveller inside the review village; tall enough for the hills at the edge.
        // K5: the south side opens onto A2 and the west side onto A3 (streamed in by QingxiBlockStreamer), so only
        // the east is walled until that block exists (the north opens onto D1, the forest edge).
        static void Boundary(Transform village)
        {
            foreach (var (x, z, w, d) in new[] { (45f, 0f, 1f, 90f) })
            {
                var wall = new GameObject("Boundary"); wall.transform.SetParent(village, false);
                wall.transform.localPosition = new Vector3(x, 5, z);
                wall.AddComponent<BoxCollider>().size = new Vector3(w, 12, d);
            }
        }

        internal static GameObject Player(Transform village, Vector3 spawn)
        {
            var player = new GameObject("Player_FirstPerson");
            player.transform.SetParent(village, false);
            player.transform.position = spawn + Vector3.up * .05f;
            var cc = player.AddComponent<CharacterController>(); cc.radius = .35f; cc.height = 1.4f; cc.center = Vector3.up * .7f; cc.slopeLimit = 35; cc.stepOffset = .3f; cc.skinWidth = .03f;
            var camGo = new GameObject("PlayerCamera") { tag = "MainCamera" }; camGo.transform.SetParent(player.transform, false); camGo.transform.localPosition = Vector3.up * 1.2f;
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = 70; cam.nearClipPlane = .05f; cam.farClipPlane = 400; camGo.AddComponent<AudioListener>();
            UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(cam).renderPostProcessing = true;
            // Original novice study mesh (saved AI three-view first); a walk-through avatar, not Heroine-01.
            var body = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/QingxiWorld/Models/ArtV001/NoviceCultivatorV1.fbx"));
            body.name = "Body_NoviceCultivatorV1"; body.transform.SetParent(player.transform, false);
            body.AddComponent<QingxiNoviceMotion>();
            var fp = player.AddComponent<global::QingxiWorld.QingxiFirstPerson>(); fp.cam = cam; fp.body = body;
            return player;
        }

        // ------------------------------------------------------------------ collaborator pieces outside the three kits
        static Transform qiPost, blockPost, shelterSpot;

        static Transform TrainingYard(Transform village, QingxiCollaboratorZonesBuilder.Result result)
        {
            var yard = new GameObject("CollaboratorZone_A_TrainingYard (Johnnnny0823)").transform;
            yard.SetParent(village, false); yard.position = At(15, -2);
            yard.rotation = Quaternion.Euler(0, Facing(yard.position, Vector3.zero), 0);
            QingxiCollaboratorZonesBuilder.PlaceTrainingProp("training-shelter", yard, new Vector3(0, 0, 4), 180, result);
            // His two posts run his drills (QingxiTrainingPractice); the core group's 引氣訣 moves under the shelter.
            qiPost = QingxiCollaboratorZonesBuilder.PlaceTrainingProp("qi-striking-post", yard, new Vector3(-2.2f, 0, .5f), 0, result).transform;
            blockPost = QingxiCollaboratorZonesBuilder.PlaceTrainingProp("agility-post", yard, new Vector3(0, 0, .2f), 0, result).transform;
            shelterSpot = new GameObject("TrainingSpot_Shelter").transform;
            shelterSpot.SetParent(yard, false); shelterSpot.localPosition = new Vector3(0, 0, 4.2f);
            QingxiCollaboratorZonesBuilder.PlaceTrainingProp("engraved-training-stone", yard, new Vector3(2.4f, 0, .4f), 200, result);
            QingxiCollaboratorZonesBuilder.PlaceTrainingProp("weapon-rack", yard, new Vector3(4, 0, 3), 270, result);
            QingxiCollaboratorZonesBuilder.PlaceTrainingProp("training-banner", yard, new Vector3(-3.8f, 0, -2.2f), 0, result);
            return yard;
        }

        static Transform[] Signs(Transform village, QingxiCollaboratorZonesBuilder.Result result)
        {
            var root = new GameObject("VillageSigns (Eli-0731)").transform; root.SetParent(village, false);
            var places = new[] {
                ("Q01", new Vector3(2.6f, 0, -12f), 0f),      // notice board at the plaza approach
                ("Q02", new Vector3(10.5f, 0, -6.5f), -60f),  // clue toward the training yard
                ("Q03", new Vector3(2.4f, 0, 9.5f), 180f),    // clue on the forest path
                ("Q04", new Vector3(-10.5f, 0, -6.5f), 60f),  // clue toward the alchemy corner
            };
            return places.Select(p =>
            {
                var model = QingxiCollaboratorZonesBuilder.PlaceConverted(QingxiCollaboratorZonesBuilder.SignModels, p.Item1, root, At(p.Item2), p.Item3, result);
                var marker = new GameObject("TrailClue_" + p.Item1).transform;
                marker.SetParent(root, false); marker.localPosition = At(p.Item2 + Quaternion.Euler(0, p.Item3, 0) * new Vector3(0, 0, -1.2f));
                return marker;
            }).ToArray();
        }

        // Herb nodes for the local foraging loop use joshsu54's gathering kit (QX_SpiritHerb_*): the "pre"
        // model until harvested, the "post" model until it regrows (QingxiHerbVisual).
        static Transform[] Herbs(Transform village)
        {
            CopyGathering();
            var root = new GameObject("HerbNodes (joshsu54 gathering kit)").transform; root.SetParent(village, false);
            return layout.herbs.Select(h =>
            {
                var node = new GameObject(h.id).transform; node.SetParent(root, false); node.localPosition = At(h.x, h.z);
                var visual = node.gameObject.AddComponent<QingxiHerbVisual>();
                visual.pre = HerbModel(h.kind, "pre", node);
                visual.post = HerbModel(h.kind, "post", node);
                visual.post.SetActive(false);
                return node;
            }).ToArray();
        }

        static GameObject HerbModel(string kind, string state, Transform node)
        {
            string key = $"QX_SpiritHerb_{kind}_{state}";
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"{GatheringModels}/{kind}/{key}.fbx");
            if (source == null) throw new FileNotFoundException("Gathering kit herb missing", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = key + " - by joshsu54";
            model.transform.SetParent(node, false);
            var material = GatheringMaterial(kind, key);
            foreach (var r in model.GetComponentsInChildren<Renderer>()) r.sharedMaterials = Enumerable.Repeat(material, r.sharedMaterials.Length).ToArray();
            return model;
        }

        static Material GatheringMaterial(string kind, string key)
        {
            var path = $"{MaterialFolder}/{key}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            string tex = $"{GatheringModels}/{kind}/textures/{key}_";
            var baseColor = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "BaseColor.png");
            if (baseColor == null) throw new FileNotFoundException("Gathering kit texture missing", tex + "BaseColor.png");
            mat.SetTexture("_BaseMap", baseColor); mat.SetColor("_BaseColor", Color.white); mat.SetFloat("_Smoothness", .15f);
            var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "Normal.png");
            if (normal != null) { mat.SetTexture("_BumpMap", normal); mat.EnableKeyword("_NORMALMAP"); }
            var emission = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "Emission.png");
            if (emission != null) { mat.SetTexture("_EmissionMap", emission); mat.SetColor("_EmissionColor", Color.white * .6f); mat.EnableKeyword("_EMISSION"); }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Copy the two herb kinds (pre/post FBX and textures) from art/exports into the gitignored model folder.
        static void CopyGathering()
        {
            string repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            // Herb kinds go to GatheringB/<kind>; the creek's stepping plank and reeds to GatheringB/Creek.
            var kits = layout.herbs.Select(h => h.kind).Distinct().Select(k => (folder: "QX_SpiritHerb_" + k, kind: k))
                .Concat(new[] { (folder: "QX_CreekSteppingPlank", kind: "Creek"), (folder: "QX_WaterReeds", kind: "Creek") });
            foreach (var (folder, kind) in kits)
            {
                var src = Path.Combine(repo, "art/exports/qingxi-gathering-visual-kit-v1", folder, "v001");
                var dst = Path.Combine(repo, "apps/game", GatheringModels, kind);
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
            }
            AssetDatabase.Refresh();
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { GatheringModels }))
            {
                var importer = (ModelImporter)AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(guid));
                if (importer.bakeAxisConversion && importer.materialImportMode == ModelImporterMaterialImportMode.None) continue;
                importer.bakeAxisConversion = true; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
                importer.materialImportMode = ModelImporterMaterialImportMode.None;
                importer.SaveAndReimport();
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { GatheringModels }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                bool normal = path.EndsWith("_Normal.png"), linear = normal || path.EndsWith("_Roughness.png");
                var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                if (ti.textureType == type && ti.sRGBTexture == !linear && ti.maxTextureSize == 1024) continue;
                ti.textureType = type; ti.sRGBTexture = !linear; ti.maxTextureSize = 1024; ti.SaveAndReimport();
            }
        }

        // ------------------------------------------------------------------ west creek
        // Water surface ribbon along the carved channel, joshsu54's stepping planks for a crossing, and a few of his
        // reed clumps plus CollaboratorWorldV1 mossy boulders on the banks. The reeds are 35k triangles each, so only
        // a handful are placed until the clump gets a LOD.
        static void Creek(Transform village)
        {
            var c = layout.creek;
            if (c == null || c.Count < 2) return;
            // D3: the river tiles of PR #45 carry their own water, banks and grass (QingxiWaterheadA.RiverKit).
            if (layout.creekKit != null && layout.creekKit.Length > 0) return;
            var root = new GameObject("WestCreek (novice-village.json)").transform; root.SetParent(village, false);

            // Resample the centre line every metre so the ribbon bends smoothly.
            var line = new System.Collections.Generic.List<Vector2>();
            for (int i = 0; i + 1 < c.Count; i++)
            {
                int steps = Mathf.Max(1, Mathf.CeilToInt(Vector2.Distance(c[i], c[i + 1])));
                for (int s = 0; s < steps; s++) line.Add(Vector2.Lerp(c[i], c[i + 1], s / (float)steps));
            }
            line.Add(c[c.Count - 1]);
            var verts = new System.Collections.Generic.List<Vector3>(); var uvs = new System.Collections.Generic.List<Vector2>();
            var tris = new System.Collections.Generic.List<int>();
            float half = c.width * .5f - .15f, along = 0;   // tucked just inside the banks
            for (int i = 0; i < line.Count; i++)
            {
                var dir = (line[Mathf.Min(i + 1, line.Count - 1)] - line[Mathf.Max(i - 1, 0)]).normalized;
                var side = new Vector2(-dir.y, dir.x) * half;
                float y = QingxiVillageTerrain.WaterHeight(layout, line[i].x, line[i].y);
                if (i > 0) along += Vector2.Distance(line[i], line[i - 1]);
                verts.Add(new Vector3(line[i].x - side.x, y, line[i].y - side.y)); uvs.Add(new Vector2(0, along / 4f));
                verts.Add(new Vector3(line[i].x + side.x, y, line[i].y + side.y)); uvs.Add(new Vector2(1, along / 4f));
                if (i > 0) { int b = verts.Count - 4; tris.AddRange(new[] { b, b + 2, b + 1, b + 1, b + 2, b + 3 }); }
            }
            // Faces must point up or the surface is back-face culled from above (it rendered as thin slivers).
            var n = Vector3.Cross(verts[tris[1]] - verts[tris[0]], verts[tris[2]] - verts[tris[0]]);
            if (n.y < 0) for (int i = 0; i < tris.Count; i += 3) (tris[i + 1], tris[i + 2]) = (tris[i + 2], tris[i + 1]);
            var mesh = new Mesh { name = "WestCreekWater" };
            mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            if (c.crossing != null)
            {
                float ground = At(c.crossing.x, c.crossing.z).y;
                QingxiVillageTerrain.CreekDistance(layout, c.crossing.x, c.crossing.z, out float land);
                Debug.Log($"QINGXI_CREEK: crossing land {land:0.00} m, terrain bed {ground:0.00} m, water {QingxiVillageTerrain.WaterHeight(layout, c.crossing.x, c.crossing.z):0.00} m, ribbon vertices {verts.Count}");
            }
            // One mesh per block: blocks used to share one asset path and overwrite each other's water.
            AssetDatabase.CreateAsset(mesh, $"Assets/YunJing/Generated/{(string.IsNullOrEmpty(layout.block) ? "NoviceVillage" : layout.block)}CreekWater.asset");
            var water = new GameObject("CreekWater");
            water.transform.SetParent(root, false);
            water.AddComponent<MeshFilter>().sharedMesh = mesh;
            water.AddComponent<MeshRenderer>().sharedMaterial = WaterMaterial();

            // Stepping planks across the channel at the crossing (perpendicular to the flow).
            if (c.crossing != null && c.crossing.stones > 0)
            {
                var flow = FlowAt(c, new Vector2(c.crossing.x, c.crossing.z));
                var across = new Vector2(-flow.y, flow.x);
                for (int i = 0; i < c.crossing.stones; i++)
                {
                    float t = (i - (c.crossing.stones - 1) / 2f) * 1.15f;
                    var p = new Vector2(c.crossing.x, c.crossing.z) + across * t;
                    var plank = GatheringProp("QX_CreekSteppingPlank", root, p, Mathf.Atan2(across.x, across.y) * Mathf.Rad2Deg + (i % 2) * 12f);
                    var b = plank.GetComponentsInChildren<Renderer>().Select(r => r.bounds).Aggregate((x, y) => { x.Encapsulate(y); return x; });
                    var box = plank.AddComponent<BoxCollider>();
                    box.center = plank.transform.InverseTransformPoint(b.center);
                    var size = plank.transform.InverseTransformVector(b.size);
                    box.size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
                }
            }

            // Banks: reeds near the crossing, boulders spaced along the creek, alternating sides.
            var boulder = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/MossBoulderSet_v001.fbx");
            float total = 0; for (int i = 1; i < line.Count; i++) total += Vector2.Distance(line[i], line[i - 1]);
            int placed = 0;
            for (float d = 6f; d < total - 6f; d += 11f, placed++)
            {
                var (p, flow) = PointAlong(line, d);
                var bank = p + new Vector2(-flow.y, flow.x) * (placed % 2 == 0 ? 1 : -1) * (c.width * .5f + .6f);
                if (QingxiVillageTerrain.PadDistance(layout, bank.x, bank.y, out _) < 1.5f || QingxiVillageTerrain.RoadDistance(layout, bank.x, bank.y, out _) < 1.5f) continue;
                if (boulder != null)
                {
                    var rock = (GameObject)PrefabUtility.InstantiatePrefab(boulder);
                    rock.name = "CreekBoulder - MossBoulderSet_v001 (CollaboratorWorldV1)";
                    rock.transform.SetParent(root, false);
                    rock.transform.localRotation = Quaternion.Euler(0, placed * 67f, 0) * boulder.transform.localRotation;
                    rock.transform.localScale = boulder.transform.localScale * .55f;
                    rock.transform.localPosition = At(bank.x, bank.y) + Vector3.down * .2f;
                    MossStone(rock);
                }
            }
            if (c.crossing != null)
                foreach (var (dx, dz, yaw) in new[] { (-3.2f, 2.4f, 20f), (3.4f, 1.6f, 140f), (-2.6f, -3.0f, 250f), (3.0f, -2.7f, 300f) })
                {
                    var at = new Vector2(c.crossing.x + dx, c.crossing.z + dz);
                    if (QingxiVillageTerrain.CreekDistance(layout, at.x, at.y, out _) < c.width * .5f - .2f) continue;
                    GatheringProp("QX_WaterReeds", root, at, yaw);
                }
        }

        static Vector2 FlowAt(QingxiVillageTerrain.Creek c, Vector2 p)
        {
            float best = float.MaxValue; var flow = Vector2.up;
            for (int i = 0; i + 1 < c.Count; i++)
            {
                Vector2 a = c[i], b = c[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
                float d = Vector2.Distance(p, a + ab * t);
                if (d < best) { best = d; flow = ab.normalized; }
            }
            return flow;
        }

        static (Vector2 point, Vector2 flow) PointAlong(System.Collections.Generic.List<Vector2> line, float distance)
        {
            for (int i = 1; i < line.Count; i++)
            {
                float seg = Vector2.Distance(line[i - 1], line[i]);
                if (distance <= seg) return (Vector2.Lerp(line[i - 1], line[i], distance / seg), (line[i] - line[i - 1]).normalized);
                distance -= seg;
            }
            return (line[line.Count - 1], (line[line.Count - 1] - line[line.Count - 2]).normalized);
        }

        static GameObject GatheringProp(string key, Transform parent, Vector2 at, float yaw)
        {
            var source = AssetDatabase.LoadAssetAtPath<GameObject>($"{GatheringModels}/Creek/{key}.fbx");
            if (source == null) throw new FileNotFoundException("Creek prop missing", key);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            model.name = key + " - by joshsu54";
            model.transform.SetParent(parent, false);
            model.transform.localRotation = Quaternion.Euler(0, yaw, 0) * source.transform.localRotation;
            model.transform.localPosition = At(at.x, at.y);
            var material = GatheringMaterial("Creek", key);
            foreach (var r in model.GetComponentsInChildren<Renderer>()) r.sharedMaterials = Enumerable.Repeat(material, r.sharedMaterials.Length).ToArray();
            return model;
        }

        static Material WaterMaterial()
        {
            var path = $"{MaterialFolder}/{(string.IsNullOrEmpty(layout.block) ? "Village" : layout.block)}CreekWater_URP.mat";   // per block: _Width is the block's creek width
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            // Flowing water (K1): ripples drifting downstream, shallow banks, sky reflection, sun glints, foam.
            var water = Shader.Find("YunJing/QingxiCreekWater");
            if (water != null)
            {
                mat.shader = water;
                mat.SetFloat("_Width", layout.creek.width);
                mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                EditorUtility.SetDirty(mat);
                return mat;
            }
            // Fallback: clear blue-green, transparent, glossy URP Lit.
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);
            mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            mat.SetColor("_BaseColor", new Color(.10f, .34f, .36f, .72f));
            mat.SetFloat("_Smoothness", .95f);
            mat.SetFloat("_Metallic", 0);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Buildings and props from the slot registry (novice-village.json): each stands on its pad at the
        // terrain height and keeps its FBX root rotation (Z-up exports carry an import rotation); only the yaw
        // is added. Slots still waiting for a model are shown as a labelled box of their exact footprint, so the
        // planned village can be walked before the models exist. Models larger than their footprint are logged.
        static int Placements(Transform village)
        {
            var root = new GameObject("VillagePlacements (novice-village.json)").transform; root.SetParent(village, false);
            var all = layout.placements.Concat(layout.crossingSlots ?? new QingxiVillageTerrain.Placement[0]);
            int needed = 0, oversize = 0;
            foreach (var p in all)
            {
                if (p.Needed) { PlannedSlot(root, p); needed++; continue; }
                var source = AssetDatabase.LoadAssetAtPath<GameObject>(p.model);
                if (source == null) throw new FileNotFoundException("Village placement model missing (Git LFS pulled?)", p.model);
                var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
                model.name = $"{p.id} - {p.author}";
                model.transform.SetParent(root, false);
                // PR #45 pieces: LOD group and their own convex collision shells.
                if (QingxiWaterheadA.Owns(p.model)) QingxiWaterheadA.Prepare(model, walkable: false);
                // Layout proxies (the 3 × 5 m plate under Eli-0731's assembled corner) mark an area, they are not ground.
                foreach (var proxy in model.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("layout_proxy")).ToArray())
                    UnityEngine.Object.DestroyImmediate(proxy.gameObject);
                model.transform.localRotation = Quaternion.Euler(0, p.yaw, 0) * source.transform.localRotation;
                if (p.scale > 0) model.transform.localScale *= p.scale;
                model.transform.localPosition = At(p.x, p.z);
                // Rest the visual base on the ground even when the FBX origin is not at the base.
                var renderers = model.GetComponentsInChildren<Renderer>();
                if (renderers.Length == 0) throw new InvalidDataException("No renderer in " + p.model);
                var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                model.transform.position += Vector3.up * (At(p.x, p.z).y - b.min.y);
                if (p.collider == "box")
                {
                    b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                    var box = model.AddComponent<BoxCollider>();
                    box.center = model.transform.InverseTransformPoint(b.center);
                    var size = model.transform.InverseTransformVector(b.size);
                    box.size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
                }
                else if (p.collider == "pillars")
                {
                    // Gates and archways: solid 0.6 m posts at both ends of the slot's width, the opening walkable.
                    b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                    var pillars = new GameObject("Pillars").transform;
                    pillars.SetParent(model.transform.parent, false);
                    pillars.position = new Vector3(b.center.x, b.min.y, b.center.z);
                    pillars.rotation = Quaternion.Euler(0, p.yaw, 0);
                    float half = (p.footprint != null ? Mathf.Min(p.footprint[0], Mathf.Max(b.size.x, b.size.z)) : Mathf.Max(b.size.x, b.size.z)) / 2 - .3f;
                    foreach (var side in new[] { -1f, 1f })
                    {
                        var post = pillars.gameObject.AddComponent<BoxCollider>();
                        post.center = new Vector3(side * half, b.size.y / 2, 0);
                        post.size = new Vector3(.6f, b.size.y, .6f);
                    }
                }
                if (p.footprint != null && p.footprint.Length == 3)
                {
                    b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                    // Compare in the slot's own frame: world bounds of a yawed model include the rotation.
                    float a = p.yaw * Mathf.Deg2Rad, c = Mathf.Abs(Mathf.Cos(a)), s = Mathf.Abs(Mathf.Sin(a));
                    float wantX = p.footprint[0] * c + p.footprint[1] * s, wantZ = p.footprint[0] * s + p.footprint[1] * c;
                    if (b.size.x > wantX * 1.1f + .1f || b.size.z > wantZ * 1.1f + .1f || b.size.y > p.footprint[2] * 1.1f + .1f)
                    {
                        oversize++;
                        Debug.LogWarning($"QINGXI_FOOTPRINT {p.id}: model {b.size.x:F1} × {b.size.z:F1} × {b.size.y:F1} m exceeds slot {wantX:F1} × {wantZ:F1} × {p.footprint[2]:F1} m");
                    }
                }
            }
            Debug.Log($"QINGXI_SLOTS: {all.Count()} slots, {needed} waiting for models (shown as boxes), {oversize} models larger than their slot");
            return all.Count();
        }

        // A labelled box of the slot's footprint, coloured by owner, so the plan is visible in the game.
        // `at` places the frame directly (interior scenes have no village terrain to sample).
        internal static Transform PlannedSlot(Transform root, QingxiVillageTerrain.Placement p, Vector3? at = null)
        {
            var fp = p.footprint ?? new[] { 2f, 2f, 2f };
            var slot = new GameObject($"PlannedSlot {p.id} - {p.owner}").transform;
            slot.SetParent(root, false);
            slot.localPosition = at ?? At(p.x, p.z); slot.localRotation = Quaternion.Euler(0, p.yaw, 0);
            // An outline frame (12 thin edges) and a faint floor plate: reads as a plan, never fills the camera's
            // view when the player walks into it, and has no collider (the gate slot sits on the entry road).
            var colour = p.owner == "codex" ? new Color(.37f, .66f, .60f, .85f) : p.owner == "core" ? new Color(.48f, .55f, .62f, .85f) : new Color(.72f, .58f, .42f, .85f);
            var edgeMat = PlannedSlotMaterial(p.owner, colour);
            var plateMat = PlannedSlotMaterial(p.owner + "_Plate", new Color(colour.r, colour.g, colour.b, .22f));
            void Bar(string name, Vector3 centre, Vector3 size, Material mat)
            {
                var bar = GameObject.CreatePrimitive(PrimitiveType.Cube);
                bar.name = name; bar.transform.SetParent(slot, false);
                bar.transform.localPosition = centre; bar.transform.localScale = size;
                UnityEngine.Object.DestroyImmediate(bar.GetComponent<Collider>());
                bar.GetComponent<Renderer>().sharedMaterial = mat;
                bar.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            float hw = fp[0] / 2, hd = fp[1] / 2, h = fp[2], t = .06f;
            Bar("Footprint Plate", new Vector3(0, .02f, 0), new Vector3(fp[0], .02f, fp[1]), plateMat);
            foreach (var y in new[] { t / 2, h - t / 2 })
            {
                Bar("Edge", new Vector3(0, y, -hd), new Vector3(fp[0], t, t), edgeMat); Bar("Edge", new Vector3(0, y, hd), new Vector3(fp[0], t, t), edgeMat);
                Bar("Edge", new Vector3(-hw, y, 0), new Vector3(t, t, fp[1]), edgeMat); Bar("Edge", new Vector3(hw, y, 0), new Vector3(t, t, fp[1]), edgeMat);
            }
            foreach (var x in new[] { -hw, hw }) foreach (var z in new[] { -hd, hd }) Bar("Edge", new Vector3(x, h / 2, z), new Vector3(t, h, t), edgeMat);
            // The front edge (+Z) in gold, so the facing reads in the game as on the plan map.
            Bar("Front", new Vector3(0, .05f, hd), new Vector3(fp[0], .1f, .12f), PlannedSlotMaterial("Front", new Color(.91f, .78f, .47f, .9f)));
            var font = AssetDatabase.LoadAssetAtPath<Font>("Assets/YunJing/Resources/Fonts/NotoSansTC-Subset.ttf");
            var label = new GameObject("Label").AddComponent<TextMesh>();
            label.transform.SetParent(slot, false);
            label.transform.localPosition = new Vector3(0, fp[2] + .5f, 0);
            label.text = $"{p.role}\n{p.id}・{p.owner}・{fp[0]:0.#}×{fp[1]:0.#}×{fp[2]:0.#} m";
            label.anchor = TextAnchor.LowerCenter; label.alignment = TextAlignment.Center;
            label.characterSize = .045f; label.fontSize = 64; label.color = new Color(.11f, .12f, .12f);
            if (font != null) { label.font = font; label.GetComponent<MeshRenderer>().sharedMaterial = font.material; }
            label.gameObject.AddComponent<QingxiBillboard>();
            return slot;
        }

        static Material PlannedSlotMaterial(string owner, Color colour)
        {
            var path = $"{MaterialFolder}/PlannedSlot_{owner}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);
            mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.SetFloat("_ZWrite", 0);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            mat.SetColor("_BaseColor", colour); mat.SetFloat("_Smoothness", .1f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Existing reviewed environment pieces (CollaboratorWorldV1) framing the village edge.
        // K5: another block's content built by the village code on that block's data and terrain: slots (models
        // or labelled frames), the brook with its water, a scatter of pines and bamboo, and plant wind.
        internal static void BuildBlock(Transform root, QingxiVillageTerrain.Layout blockLayout, Terrain blockTerrain, string blockId)
        {
            var (oldLayout, oldTerrain) = (layout, terrain);
            layout = blockLayout; terrain = blockTerrain;
            try
            {
                bool upstream = layout.creekKit != null && layout.creekKit.Length > 0;
                if (upstream || layout.creek != null) QingxiWaterheadA.Copy();   // river tiles; sedge for every creek bank
                Placements(root);
                Creek(root);
                if (upstream) QingxiWaterheadA.RiverKit(root, layout);
                if (upstream && layout.placements.Any(p => p.id == "D3_CrackedSluice")) UpstreamClues(root);
                Dressing(root, blockId);
                Debug.Log("QINGXI_WIND (block): " + WindFoliage(root) + " foliage renderers sway");
            }
            finally { layout = oldLayout; terrain = oldTerrain; }
        }

        // D3: the three places where the upstream clues are read (server waterline.json observations). The
        // cracked sluice and the nursery tracks are their slots; the silt is read from the bank beside the silt bar.
        static void UpstreamClues(Transform parent)
        {
            var clues = new GameObject("UpstreamClues (observe-upstream)").AddComponent<QingxiUpstreamClues>();
            clues.transform.SetParent(parent, false);
            Transform Point(string name, Vector2 at)
            {
                var t = new GameObject("Clue " + name).transform; t.SetParent(clues.transform, false);
                t.position = At(at.x, at.y); return t;
            }
            Vector2 Slot(string id)
            {
                var p = layout.placements.FirstOrDefault(s => s.id == id);
                if (p == null) throw new InvalidDataException("D3 slot missing: " + id);
                return new Vector2(p.x, p.z);
            }
            var silt = QingxiWaterheadA.SiltPoint(layout);
            var trail = layout.nodes.OrderBy(n => Vector2.Distance(new Vector2(n.x, n.z), silt)).First();
            var bank = silt + (new Vector2(trail.x, trail.z) - silt).normalized * 3.2f;
            clues.siltBlocked = QingxiWaterheadA.SiltBlocked; clues.siltCleared = QingxiWaterheadA.SiltCleared;
            clues.points = new[]
            {
                new QingxiUpstreamClues.Clue { id = "cracked_sluice", at = Point("cracked_sluice", Slot("D3_CrackedSluice")) },
                new QingxiUpstreamClues.Clue { id = "silt_buildup", at = Point("silt_buildup", bank) },
                new QingxiUpstreamClues.Clue { id = "nursery_tracks", at = Point("nursery_tracks", Slot("D3_NurseryTracks")) },
            };
        }

        // The dressing plan (tools/qingxi-terrain/world-dressing.json, docs/execution/novice-world-dressing-plan.md).
        [Serializable] class DressingBiome { public string id, name; public int trees, groves, boulders, grass, sedge; }
        [Serializable] class DressingBlock { public string id, biome, status; }
        [Serializable] class DressingPlan { public DressingBiome[] biomes; public DressingBlock[] blocks; }

        // Groves, not a grid: trees gather in a few groves with open ground between them, singles in the gaps;
        // bamboo by the water and pine on the dry slopes; mossy boulders in clusters of two to four, half of them
        // along the creek; withered sedge on the creek banks. Counts per 100 × 100 m come from the block's biome.
        // Nothing on pads (3.5 m), roads (3 m), the creek or within 4 m of the block edge.
        static void Dressing(Transform parent, string blockId)
        {
            var plan = JsonUtility.FromJson<DressingPlan>(File.ReadAllText(Path.Combine(Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..")), "tools/qingxi-terrain/world-dressing.json")));
            var entry = plan.blocks.FirstOrDefault(b => b.id == blockId);
            var biome = plan.biomes.FirstOrDefault(b => entry != null && b.id == entry.biome);
            if (biome == null) { BlockTrees(parent); return; }
            var root = new GameObject($"Dressing ({biome.name}, world-dressing.json)").transform; root.SetParent(parent, false);
            var pine = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/CommonPine_v001.fbx");
            var bamboo = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/BambooClump_v001.fbx");
            var boulder = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/MossBoulderSet_v001.fbx");
            if (pine == null || bamboo == null || boulder == null) throw new InvalidOperationException("CollaboratorWorldV1 pine/bamboo/boulder models missing");
            var a = layout.bounds; var random = new System.Random((int)(a.minX * 31 + a.minZ * 17) ^ blockId.GetHashCode());
            float R() => (float)random.NextDouble();
            float clear = layout.creek == null ? 0 : layout.creekKit != null && layout.creekKit.Length > 0 ? 5f : layout.creek.width * .5f + layout.creek.bank + 1;
            bool Free(float x, float z, float pad = 3.5f, float road = 3f, float creekGap = -1)
            {
                if (x < a.minX + 4 || x > a.minX + a.sizeX - 4 || z < a.minZ + 4 || z > a.minZ + a.sizeZ - 4) return false;
                // The territory hollow keeps its yard open: trees and rocks stay on the surrounding hills.
                if (layout.isolated && Mathf.Max(Mathf.Abs(x - (a.minX + a.sizeX / 2)), Mathf.Abs(z - (a.minZ + a.sizeZ / 2))) < a.sizeX * .28f) return false;
                if (QingxiVillageTerrain.PadDistance(layout, x, z, out _) < pad || QingxiVillageTerrain.RoadDistance(layout, x, z, out _) < road) return false;
                if (QingxiVillageTerrain.CreekDistance(layout, x, z, out _) < (creekGap < 0 ? clear : creekGap)) return false;
                return layout.placements == null || layout.placements.All(p => Vector2.Distance(new Vector2(p.x, p.z), new Vector2(x, z)) > 3f);
            }
            Vector2 Somewhere(Func<float, float, bool> ok)
            {
                for (int i = 0; i < 80; i++) { float x = a.minX + 4 + R() * (a.sizeX - 8), z = a.minZ + 4 + R() * (a.sizeZ - 8); if (ok(x, z)) return new Vector2(x, z); }
                return new Vector2(float.NaN, float.NaN);
            }
            int trees = 0, rocks = 0, sedges = 0, elders = 0;
            // Species built on z1nnz's Elder World Tree (QingxiElderTrees), mixed with the pines and bamboo. By the water:
            // willow and bamboo. On dry ground: pine, camphor, cypress, maple, ginkgo, plum and saplings, by weight. A
            // grove keeps one species (a stand of maples, of ginkgo, of cypress); single trees mix. Heights in metres.
            bool elder = QingxiElderTrees.Available;
            if (elder) ElderKit();
            var heights = new System.Collections.Generic.Dictionary<string, float> {
                ["ElderCamphor"] = 7.5f, ["ElderMaple"] = 5.5f, ["ElderGinkgo"] = 8f, ["ElderWillow"] = 6f,
                ["ElderPlum"] = 3.6f, ["ElderCypress"] = 9f, ["ElderSapling"] = 3.4f };
            var dry = new (string kind, float weight)[] { (null, .35f), ("ElderCamphor", .2f), ("ElderCypress", .15f), ("ElderMaple", .1f),
                ("ElderGinkgo", .08f), ("ElderPlum", .07f), ("ElderSapling", .05f) };
            string Pick((string kind, float weight)[] table) { float t = R(); foreach (var (k, w) in table) { if ((t -= w) <= 0) return k; } return table[0].kind; }
            string GroveKind() => !elder ? null : new[] { null, null, "ElderCamphor", "ElderCamphor", "ElderMaple", "ElderGinkgo", "ElderCypress" }[random.Next(7)];
            void PlantTree(float x, float z, string kind = "")
            {
                float wet = QingxiVillageTerrain.CreekDistance(layout, x, z, out _);
                bool cane = wet < 16f ? R() < .75f : R() < .15f;
                if (elder && wet < 16f && R() < .4f) { cane = false; kind = "ElderWillow"; }   // willows lean over the water
                else if (kind == "") kind = elder ? Pick(dry) : null;
                if (cane) Tree(bamboo, root, new Vector3(x, 0, z), 4.2f + R() * 1.8f, R() * 360);
                else if (kind != null)
                {
                    float h = heights[kind];
                    Tree(QingxiElderTrees.Source(kind), root, new Vector3(x, 0, z), h * (.82f + R() * .36f), R() * 360);
                    elders++;
                }
                else Tree(pine, root, new Vector3(x, 0, z), 7f + R() * 5.5f, R() * 360);
                trees++;
            }
            // Groves: about three quarters of the trees, 4–11 m around each grove centre.
            var groves = Enumerable.Range(0, biome.groves).Select(_ => Somewhere((x, z) => Free(x, z, 8f, 6f))).Where(g => !float.IsNaN(g.x)).ToList();
            var groveKinds = groves.Select(_ => GroveKind()).ToList();
            int inGroves = groves.Count == 0 ? 0 : biome.trees * 3 / 4;
            for (int i = 0, tries = 0; i < inGroves && tries < inGroves * 12; tries++)
            {
                int gi = random.Next(groves.Count); var g = groves[gi];
                float angle = R() * Mathf.PI * 2, r = 2f + R() * R() * 10f;   // denser at the heart of the grove
                float x = g.x + Mathf.Cos(angle) * r, z = g.y + Mathf.Sin(angle) * r;
                if (!Free(x, z)) continue;
                PlantTree(x, z, groveKinds[gi]); i++;
            }
            for (int i = trees; i < biome.trees; i++) { var p = Somewhere((x, z) => Free(x, z)); if (!float.IsNaN(p.x)) PlantTree(p.x, p.y); }
            // Boulder clusters; with a creek, half sit along its banks.
            int clusters = Mathf.Max(1, biome.boulders / 3);
            for (int c = 0; c < clusters; c++)
            {
                Vector2 centre;
                if (layout.creek != null && layout.creek.Count >= 2 && c % 2 == 0)
                {
                    int s = random.Next(layout.creek.Count - 1);
                    var p = Vector2.Lerp(layout.creek[s], layout.creek[s + 1], R()); var q = layout.creek[s + 1] - layout.creek[s];
                    var side = new Vector2(-q.y, q.x).normalized * ((R() < .5f ? -1 : 1) * (clear + 1.2f + R() * 3f));
                    centre = p + side;
                    if (!Free(centre.x, centre.y, 3.5f, 2.5f)) continue;
                }
                else { centre = Somewhere((x, z) => Free(x, z, 4f, 3f)); if (float.IsNaN(centre.x)) continue; }
                int count = 2 + random.Next(3);
                for (int k = 0; k < count; k++)
                {
                    float x = centre.x + (R() - .5f) * 3.2f, z = centre.y + (R() - .5f) * 3.2f;
                    if (!Free(x, z, 3.5f, 2.5f)) continue;
                    var rock = (GameObject)PrefabUtility.InstantiatePrefab(boulder);
                    rock.name = "Boulder - MossBoulderSet_v001 (CollaboratorWorldV1)";
                    rock.transform.SetParent(root, false);
                    float scale = .35f + R() * R() * .9f;
                    rock.transform.localScale *= scale;
                    rock.transform.localRotation = Quaternion.Euler(R() * 8 - 4, R() * 360, R() * 8 - 4) * boulder.transform.localRotation;
                    rock.transform.localPosition = At(x, z) + Vector3.down * (.12f + .2f * scale);
                    MossStone(rock);
                    rocks++;
                }
            }
            // Withered sedge on the creek banks (the PR #45 tufts, when the upstream kit is in this project).
            if (biome.sedge > 0 && layout.creek != null && layout.creek.Count >= 2 && File.Exists(QingxiWaterheadA.ModelPath("A05_WitheredSedge_01")))
                for (int i = 0, tries = 0; i < biome.sedge && tries < biome.sedge * 8; tries++)
                {
                    int s = random.Next(layout.creek.Count - 1);
                    var p = Vector2.Lerp(layout.creek[s], layout.creek[s + 1], R()); var q = layout.creek[s + 1] - layout.creek[s];
                    var at = p + new Vector2(-q.y, q.x).normalized * ((R() < .5f ? -1 : 1) * (clear + .3f + R() * 4.5f));
                    if (!Free(at.x, at.y, 2f, 1.5f, clear)) continue;
                    var tuft = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(QingxiWaterheadA.ModelPath("A05_WitheredSedge_0" + (1 + random.Next(3)))));
                    tuft.transform.SetParent(root, false);
                    QingxiWaterheadA.Prepare(tuft, walkable: false);
                    tuft.transform.localRotation = Quaternion.Euler(0, R() * 360, 0) * tuft.transform.localRotation;
                    tuft.transform.localPosition = At(at.x, at.y) + Vector3.down * .05f;
                    i++; sedges++;
                }
            // The territory's guardian: the Elder World Tree itself, roots and all, on the slope above the yard corner.
            if (elder && blockId == "TR")
            {
                Tree(QingxiElderTrees.Source("ElderGuardian"), root, new Vector3(-17.5f, 0, -17.5f), 9.8f, 40);
                elders++; trees++;
            }
            Debug.Log($"QINGXI_DRESSING {blockId} ({biome.name}): {trees} trees ({elders} elder-tree kin) in {groves.Count} groves, {rocks} boulders, {sedges} sedge tufts");
        }

        static bool elderCopied;
        static void ElderKit() { if (!elderCopied) { QingxiElderTrees.Copy(); elderCopied = true; } }

        // MossBoulderSet_v001 carries no texture and its source colour converts to near black under URP, so the
        // boulders get one weathered grey-green stone material.
        static void MossStone(GameObject rock)
        {
            var path = $"{MaterialFolder}/MossStone_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", new Color(.47f, .49f, .44f)); mat.SetFloat("_Smoothness", .12f);
            EditorUtility.SetDirty(mat);
            foreach (var r in rock.GetComponentsInChildren<Renderer>()) r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
        }

        // A loose grid with jitter: pines on dry ground, bamboo near water, nothing on pads, roads, the brook or
        // in the 4 m along the block edge (where neighbouring blocks meet). Fallback for blocks with no dressing plan.
        static void BlockTrees(Transform parent)
        {
            var root = new GameObject("BlockTrees (CollaboratorWorldV1)").transform; root.SetParent(parent, false);
            var pine = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/CommonPine_v001.fbx");
            var bamboo = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/BambooClump_v001.fbx");
            if (pine == null || bamboo == null) throw new InvalidOperationException("CollaboratorWorldV1 pine/bamboo models missing");
            var a = layout.bounds; var random = new System.Random((int)(a.minX * 31 + a.minZ * 17));
            for (float gx = a.minX + 6; gx < a.minX + a.sizeX - 4; gx += 9)
            for (float gz = a.minZ + 6; gz < a.minZ + a.sizeZ - 4; gz += 9)
            {
                if (random.NextDouble() > .42) continue;
                float x = gx + (float)random.NextDouble() * 6 - 3, z = gz + (float)random.NextDouble() * 6 - 3;
                if (QingxiVillageTerrain.PadDistance(layout, x, z, out _) < 3.5f || QingxiVillageTerrain.RoadDistance(layout, x, z, out _) < 3f) continue;
                float creek = QingxiVillageTerrain.CreekDistance(layout, x, z, out _);
                if (creek < 6f) continue;
                bool wet = creek < 14f;
                if (wet || random.NextDouble() < .2) Tree(bamboo, root, new Vector3(x, 0, z), 4.5f + (float)random.NextDouble(), (float)random.NextDouble() * 360);
                else Tree(pine, root, new Vector3(x, 0, z), 8f + (float)random.NextDouble() * 4, (float)random.NextDouble() * 360);
            }
        }

        static void Scenery(Transform village)
        {
            var root = new GameObject("VillageEdgeTrees (CollaboratorWorldV1)").transform; root.SetParent(village, false);
            var pine = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/CommonPine_v001.fbx");
            var bamboo = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/YunJing/Models/CollaboratorWorldV1/BambooClump_v001.fbx");
            if (pine == null || bamboo == null) throw new InvalidOperationException("CollaboratorWorldV1 pine/bamboo models missing");
            var random = new System.Random(29);
            int n = 0;
            for (float angle = 0; angle < 360; angle += 15)
            {
                var r = 30 + (float)random.NextDouble() * 8;
                var at = Quaternion.Euler(0, angle, 0) * new Vector3(0, 0, r);
                if (Mathf.Abs(at.x) < 11 && at.z < 0) continue;   // keep the village gate approach open
                // ...and every pad, road and herb clear (the layout grew into the old ring).
                if (QingxiVillageTerrain.PadDistance(layout, at.x, at.z, out _) < 3f || QingxiVillageTerrain.RoadDistance(layout, at.x, at.z, out _) < 3f
                    || QingxiVillageTerrain.CreekDistance(layout, at.x, at.z, out _) < 6f
                    || layout.herbs.Any(h => Vector2.Distance(new Vector2(h.x, h.z), new Vector2(at.x, at.z)) < 4f)) continue;
                Tree(n++ % 3 == 0 ? bamboo : pine, root, at, n % 3 == 0 ? 4.5f : 9f + (float)random.NextDouble() * 3, (float)random.NextDouble() * 360);
            }
            // a darker stand of pines behind the forest encounter
            foreach (var x in new[] { -13f, -10f, 10f, 13f, -6f, 6f })
                Tree(pine, root, new Vector3(x, 0, 30 + Mathf.Abs(x) * .3f), 10f, x * 31);
        }

        static void Tree(GameObject source, Transform parent, Vector3 at, float height, float yaw)
        {
            var tree = (GameObject)PrefabUtility.InstantiatePrefab(source);
            // Keep the FBX root's own axis rotation; only add the yaw.
            // Sink the trunk base slightly so it never shows a gap on sloped ground.
            tree.transform.SetParent(parent, false); tree.transform.localPosition = At(at) + Vector3.down * .15f;
            tree.transform.localRotation = Quaternion.Euler(0, yaw, 0) * source.transform.localRotation;
            var renderers = tree.GetComponentsInChildren<Renderer>();
            var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
            tree.transform.localScale *= height / Mathf.Max(.01f, b.size.y);
        }

        static Material Surface(string name, Color color)
        {
            var path = $"{MaterialFolder}/{name}_URP.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", color); mat.SetFloat("_Smoothness", .08f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // Additive glow for the training drills (rope bands, jade disc, qi motes, block sparks). Saved as assets so
        // the URP particle shader ships in the player builds; the dot material carries a soft round texture.
        public static void TrainingGlow(QingxiTrainingPractice training)
        {
            Directory.CreateDirectory(Path.Combine(Application.dataPath, MaterialFolder.Substring("Assets/".Length)));
            Material Glow(string name, Texture2D tex)
            {
                var path = $"{MaterialFolder}/{name}_URP.mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit")); AssetDatabase.CreateAsset(mat, path); }
                mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 2);
                mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); mat.SetFloat("_DstBlend", (float)BlendMode.One);
                mat.SetFloat("_ZWrite", 0);
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)RenderQueue.Transparent;
                mat.SetColor("_BaseColor", Color.white);
                if (tex != null) mat.SetTexture("_BaseMap", tex);
                EditorUtility.SetDirty(mat);
                return mat;
            }
            var dotPath = MaterialFolder + "/TrainingGlowDot.asset";
            var dot = AssetDatabase.LoadAssetAtPath<Texture2D>(dotPath);
            if (dot == null)
            {
                dot = new Texture2D(64, 64, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
                for (int y = 0; y < 64; y++)
                    for (int x = 0; x < 64; x++)
                    {
                        float d = Vector2.Distance(new Vector2(x + .5f, y + .5f), new Vector2(32, 32)) / 32;
                        dot.SetPixel(x, y, new Color(1, 1, 1, Mathf.Pow(Mathf.Clamp01(1 - d), 2)));
                    }
                dot.Apply();
                AssetDatabase.CreateAsset(dot, dotPath);
            }
            training.glowLine = Glow("TrainingGlowLine", null);
            training.glowDot = Glow("TrainingGlowDot", dot);
        }

        // K2: trees, bamboo, reeds and shrubs sway (YunJing/QingxiFoliageWind). Each foliage material gets a wind
        // twin that keeps its colour map, tint and alpha cut-off; the sway height and strength follow the kind of
        // plant. Matched by the name of the placed model, so a bamboo fence or a bamboo tray stays still.
        static readonly (string key, float height, float strength)[] WindKinds = {
            ("CommonPine", 7f, .12f), ("Elder", 7f, .07f), ("BambooClump", 6f, .32f), ("QX_WaterReeds", 1.8f, .12f), ("WildShrub", 1.5f, .06f),
        };

        static int WindFoliage(Transform village)
        {
            var shader = Shader.Find("YunJing/QingxiFoliageWind");
            if (shader == null) { Debug.LogWarning("QINGXI_WIND: shader missing, foliage stays still"); return 0; }
            var folder = MaterialFolder + "/Wind";
            if (!AssetDatabase.IsValidFolder(folder)) AssetDatabase.CreateFolder(MaterialFolder, "Wind");
            var twins = new System.Collections.Generic.Dictionary<(Material, string), Material>();
            int count = 0;
            foreach (var r in village.GetComponentsInChildren<MeshRenderer>(true))
            {
                (string key, float height, float strength) kind = default;
                for (var t = r.transform; t != null && t != village && kind.key == null; t = t.parent)
                    foreach (var k in WindKinds) if (t.name.Contains(k.key)) { kind = k; break; }
                if (kind.key == null) continue;
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    var source = mats[i];
                    if (source == null || source.shader == shader) continue;
                    if (!twins.TryGetValue((source, kind.key), out var twin))
                    {
                        var path = $"{folder}/{source.name}_{kind.key}_Wind.mat";
                        twin = AssetDatabase.LoadAssetAtPath<Material>(path);
                        if (twin == null) { twin = new Material(shader); AssetDatabase.CreateAsset(twin, path); }
                        twin.shader = shader;
                        var map = source.HasProperty("_BaseMap") ? source.GetTexture("_BaseMap") : source.HasProperty("_MainTex") ? source.GetTexture("_MainTex") : null;
                        twin.SetTexture("_BaseMap", map);
                        twin.SetColor("_BaseColor", source.HasProperty("_BaseColor") ? source.GetColor("_BaseColor") : source.HasProperty("_Color") ? source.GetColor("_Color") : Color.white);
                        bool clipped = source.IsKeywordEnabled("_ALPHATEST_ON") || (source.HasProperty("_AlphaClip") && source.GetFloat("_AlphaClip") > .5f);
                        twin.SetFloat("_Cutoff", clipped && source.HasProperty("_Cutoff") ? source.GetFloat("_Cutoff") : 0f);
                        twin.SetFloat("_Height", kind.height); twin.SetFloat("_Strength", kind.strength);
                        EditorUtility.SetDirty(twin);
                        twins[(source, kind.key)] = twin;
                    }
                    mats[i] = twin;
                }
                r.sharedMaterials = mats;
                count++;
            }
            return count;
        }

        static Material UiMaterial()
        {
            var path = MaterialFolder + "/VillageHudUI.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("UI/Default")); AssetDatabase.CreateAsset(mat, path); }
            return mat;
        }

        // ------------------------------------------------------------------ alchemy room link and build
        static void PrepareAlchemyRoom()
        {
            var productName = PlayerSettings.productName;
            AlchemyRoomBuilder.Generate();
            PlayerSettings.productName = productName;
            var scene = EditorSceneManager.OpenScene(AlchemyScenePath);
            new GameObject("Qingxi Return Door").AddComponent<QingxiSceneReturn>();
            if (!EditorSceneManager.SaveScene(scene, AlchemyScenePath)) throw new InvalidOperationException("Could not save " + AlchemyScenePath);
            Debug.Log("QINGXI_ALCHEMY_ROOM_LINKED: " + AlchemyScenePath);
        }

        public static void BuildWindows()
        {
            if (Scenes.Any(s => !File.Exists(s))) throw new InvalidOperationException("Generate the novice village in a previous Editor process.");
            QingxiUrpUpgrade.EnsurePipeline();
            PlayerSettings.productName = "承天 · 青溪新手村";
            PlayerSettings.SplashScreen.show = false;
            string path = "../../artifacts/windows-novice-village/YunJingNoviceVillage.exe";
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                scenes = Scenes, target = BuildTarget.StandaloneWindows64,
                locationPathName = path, options = BuildOptions.None
            });
            if (report.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Novice village Windows build failed.");
            Debug.Log("QINGXI_NOVICE_VILLAGE_WINDOWS_BUILT: " + Path.GetFullPath(path));
        }

        // Browser build with the YunJing PWA template (Codex C3: web manifest, service worker, installable;
        // no Unity branding). Gzip with the
        // decompression fallback so any static server can host it; run tools/qingxi-webgl/serve.mjs to try it.
        public static void BuildWebGL()
        {
            if (Scenes.Any(s => !File.Exists(s))) throw new InvalidOperationException("Generate the novice village in a previous Editor process.");
            QingxiUrpUpgrade.EnsurePipeline();
            PlayerSettings.productName = "承天 · 青溪新手村";
            PlayerSettings.SplashScreen.show = false;   // the Unity logo alone is 2.7 MB of the download
            PlayerSettings.WebGL.template = "PROJECT:YunJing";   // Codex C3 shell + entry layer (docs/art/loading-experience-v1.md)
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Brotli;   // K6: ~15–20% smaller than gzip
            PlayerSettings.WebGL.decompressionFallback = true;
            PlayerSettings.WebGL.dataCaching = true;
            PlayerSettings.WebGL.exceptionSupport = WebGLExceptionSupport.ExplicitlyThrownExceptionsOnly;
            PlayerSettings.WebGL.initialMemorySize = 256;
            PlayerSettings.runInBackground = true;
            string path = "../../artifacts/webgl-novice-village";
            Directory.CreateDirectory(path);
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                scenes = Scenes, target = BuildTarget.WebGL, locationPathName = path, options = BuildOptions.None
            });
            if (report.summary.result != BuildResult.Succeeded)
                throw new InvalidOperationException("Novice village WebGL build failed: " + string.Join("; ", report.steps.SelectMany(s => s.messages).Where(m => m.type == LogType.Error).Select(m => m.content).Take(5)));
            Debug.Log($"QINGXI_NOVICE_VILLAGE_WEBGL_BUILT: {Path.GetFullPath(path)} ({report.summary.totalSize / 1048576f:0.0} MB, {report.summary.totalTime.TotalMinutes:0.0} min)");
        }
    }
}
