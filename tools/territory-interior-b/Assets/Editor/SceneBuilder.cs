using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// Builds Assets/Scenes/TI18_InteriorDemo.unity from the TerritoryInterior18 FBX/texture sets.
/// Layout follows the brief's slot table (scene x,z = Unity x,z); every model's front (Blender -Y) imports as Unity +Z.
public static class SceneBuilder
{
    const string Art = "Assets/Art", Gen = "Assets/Generated", ScenePath = "Assets/Scenes/TI18_InteriorDemo.unity";
    static readonly Dictionary<string, float> Face = new Dictionary<string, float> { { "-x", -90f }, { "+x", 90f }, { "-z", 180f }, { "+z", 0f } };

    public static readonly List<string> Report = new List<string>();

    [MenuItem("TI18/Build Interior Demo Scene")]
    public static void BuildMenu() { Build(); }

    public static GameObject Build()
    {
        Report.Clear();
        ConfigureImporters();
        Directory.CreateDirectory(Gen + "/Materials"); Directory.CreateDirectory("Assets/Scenes");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // ---------------------------------------------------------------- lighting & room shell
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(.36f, .33f, .30f);
        QualitySettings.shadows = ShadowQuality.All; QualitySettings.shadowResolution = ShadowResolution.VeryHigh;
        QualitySettings.shadowDistance = 18f; QualitySettings.pixelLightCount = 8; QualitySettings.antiAliasing = 4;
        var sunGo = new GameObject("Dusk_Sun"); var sun = sunGo.AddComponent<Light>();
        sun.type = LightType.Directional; sun.color = new Color(1f, .80f, .58f); sun.intensity = .85f; sun.shadows = LightShadows.Soft;
        sunGo.transform.rotation = Quaternion.Euler(48f, 28f, 0f);

        var room = new GameObject("Room_Placeholder_Not_Delivered");
        var floorM = Plain("Floor_Planks", new Color(.30f, .19f, .11f), .25f);
        var wallM = Plain("Wall_Plaster", new Color(.62f, .57f, .49f), .1f);
        var trimM = Plain("Wall_Trim", new Color(.22f, .13f, .07f), .2f);
        Slab(room, "Floor", new Vector3(0, -.05f, 0), new Vector3(7.3f, .1f, 5.3f), floorM);
        // interface: 7 m × 5 m × 3.2 m clear, front and back doors 1.2 m × 2.2 m centred
        const float H = 3.2f;
        Slab(room, "Wall_Left", new Vector3(-3.575f, H / 2f, 0), new Vector3(.15f, H, 5.3f), wallM);
        Slab(room, "Wall_Right", new Vector3(3.575f, H / 2f, 0), new Vector3(.15f, H, 5.3f), wallM);
        float side = (7f - 1.2f) / 2f;
        foreach (var sx in new[] { -1f, 1f })
            Slab(room, "Wall_Back", new Vector3(sx * (.6f + side / 2f), H / 2f, 2.575f), new Vector3(side, H, .15f), wallM);
        Slab(room, "Door_Header_Back", new Vector3(0, (2.2f + H) / 2f, 2.575f), new Vector3(1.2f, H - 2.2f, .15f), wallM);
        Slab(room, "Door_Back_Dark", new Vector3(0, 1.1f, 2.7f), new Vector3(1.3f, 2.2f, .05f), Plain("Doorway_Dusk", new Color(.10f, .12f, .16f), 0f));
        Slab(room, "Skirting_Back", new Vector3(0, .05f, 2.49f), new Vector3(7f, .1f, .03f), trimM);
        foreach (var sx in new[] { -1f, 1f }) Slab(room, "Skirting_Side", new Vector3(sx * 3.49f, .05f, 0), new Vector3(.03f, .1f, 5f), trimM);
        Slab(room, "Front_Sill", new Vector3(0, .03f, -2.58f), new Vector3(7.3f, .06f, .15f), trimM);
        // front wall + ceiling close the room for the shoulder camera (it collides with them); they cast no shadow so the dusk sun still reaches in
        var shut = new List<GameObject>
        {
            Slab(room, "Door_Header_Front", new Vector3(0, (2.2f + H) / 2f, -2.575f), new Vector3(1.2f, H - 2.2f, .15f), wallM),
            Slab(room, "Door_Front_Dark", new Vector3(0, 1.1f, -2.7f), new Vector3(1.3f, 2.2f, .05f), Plain("Doorway_Dusk", new Color(.10f, .12f, .16f), 0f)),
            Slab(room, "Ceiling", new Vector3(0, H + .05f, 0), new Vector3(7.3f, .1f, 5.3f), Plain("Ceiling_Boards", new Color(.36f, .25f, .16f), .1f)),
        };
        foreach (var sx in new[] { -1f, 1f })
        {
            shut.Add(Slab(room, "Wall_Front", new Vector3(sx * (.6f + (side + .15f) / 2f), H / 2f, -2.575f), new Vector3(side + .15f, H, .15f), wallM));
            shut.Add(Slab(room, "Skirting_Front", new Vector3(sx * (.6f + side / 2f), .05f, -2.49f), new Vector3(side, .1f, .03f), trimM));
        }
        foreach (var z in new[] { -1.6f, 0f, 1.6f }) shut.Add(Slab(room, "Ceiling_Beam", new Vector3(0, H - .05f, z), new Vector3(7f, .12f, .14f), trimM));
        foreach (var g in shut) g.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

        // ---------------------------------------------------------------- furniture (brief slot table; front wall/curtain omitted for the camera)
        var layout = new (string slot, string id, float x, float z, string face)[]
        {
            ("TI_Shelf", "TI01_BoguShelf", 3.25f, -.6f, "-x"),
            ("TI_Desk", "TI03_JournalDesk", -2.6f, -1.35f, "+x"),
            ("TI_Furnace", "TI02_HomeFurnace", 2.7f, -1.9f, "-x"),
            ("TI_Lamp_1", "TI04_PaperLamp", -1.6f, 2.1f, "-z"),
            ("TI_Lamp_2", "TI04_PaperLamp", -3.1f, -.55f, "+x"),       // against the left wall between desk and bed
            ("TI_Screen", "TI05_LandscapeScreen", -1.55f, -2.3f, "+z"), // against the front wall, left of the front door
            ("TI_Rug", "TI06_WovenMat", .6f, 0f, "-z"),
            ("TI_Curtain_B", "TI07_LinenCurtain", 0f, 2.5f, "-z"),
        };
        var placed = new Dictionary<string, GameObject>();
        foreach (var (slot, id, x, z, face) in layout)
            placed[slot] = Place(TiPath(id), slot, x, z, Face[face], true);
        var bedGo = Place(Art + "/Existing/DiscipleBed_v001.fbx", "Bed", -2.75f, 1.0f, 180f, false);
        var chestGo = Place(Art + "/Existing/StorageChest_v001.fbx", "StorageChest", 2.6f, 1.9f, 180f, false);
        Place(Art + "/Existing/MeditationCushion_v001.fbx", "Cushion", 1.2f, -.2f, 180f, false);

        // ---------------------------------------------------------------- interactables
        var player = BuildPlayer();
        var shelf = BuildShelf(placed["TI_Shelf"]);
        var chest = BuildChest(chestGo);
        var furnace = BuildFurnace(placed["TI_Furnace"]);
        var lamp = BuildLamp(placed["TI_Lamp_2"], true);
        var sideLamp = BuildLamp(placed["TI_Lamp_1"], false);
        var bed = BuildBed(bedGo, player);
        furnace.pantryChest = chest;
        var items = new Interactable[] { chest, shelf, furnace, lamp, bed };

        // ---------------------------------------------------------------- camera, UI, control
        var camGo = new GameObject("Main Camera"); camGo.tag = "MainCamera";
        var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = 50f; cam.nearClipPlane = .05f; cam.depthTextureMode = DepthTextureMode.None; cam.farClipPlane = 60f;
        cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.06f, .065f, .075f); cam.allowMSAA = true;
        var rig = camGo.AddComponent<CameraRig>(); rig.target = player.transform; rig.shots = items;
        rig.yaw = 0f; rig.pitch = 16f; rig.distance = 2.2f;

        var canvasGo = new GameObject("UI", typeof(RectTransform));
        var canvas = canvasGo.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = cam; canvas.planeDistance = .105f;
        var scaler = canvasGo.AddComponent<CanvasScaler>(); scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1280, 720); scaler.matchWidthOrHeight = .5f;
        canvasGo.AddComponent<GraphicRaycaster>();
        var ui = canvasGo.AddComponent<InteriorUI>();
        var iconDefs = new (string item, string key, System.Func<GameObject> make)[]
        {
            ("青瓷罐", "TI08c_CeladonJar", () => Place(TiPath("TI08c_CeladonJar"), "Icon", 0, 0, 0, true)),
            ("卷軸", "TI08b_PaperScroll", () => Place(TiPath("TI08b_PaperScroll"), "Icon", 0, 0, 0, true)),
            ("木匣", "TI08a_KeepsakeBox", () => Place(TiPath("TI08a_KeepsakeBox"), "Icon", 0, 0, 0, true)),
            ("藥罐", "TI08d_MedicinePot", () => Place(TiPath("TI08d_MedicinePot"), "Icon", 0, 0, 0, true)),
            ("青靈草", "SpiritHerbMature", () => Prop(Art + "/Existing/SpiritHerbMature_v001.fbx", "Icon", 1f)),
            ("淨水蓮", "WaterLotus_Standin", () => Lotus("Icon", 1f)),
            ("松柴", "FirewoodStack", () => Prop(Art + "/Existing/FirewoodStack_v002.fbx", "Icon", 1f)),
            ("回春丹", "QPillBottle", () => Prop(Art + "/Existing/QPillBottle_v002.fbx", "Icon", 1f)),
        };
        ui.iconNames = iconDefs.Select(d => d.item).ToArray();
        ui.icons = iconDefs.Select(d => RenderIcon(d.key, d.make())).ToArray();
        // landscape only on phones / tablets (touch overlay lives in InteriorUI / TouchControls)
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
        PlayerSettings.allowedAutorotateToPortrait = PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
        PlayerSettings.allowedAutorotateToLandscapeLeft = PlayerSettings.allowedAutorotateToLandscapeRight = true;
        var es = new GameObject("EventSystem"); es.AddComponent<EventSystem>(); es.AddComponent<StandaloneInputModule>();

        var ctl = player.gameObject.AddComponent<PlayerController>(); ctl.avatar = player; ctl.interactables = items; ctl.rig = rig;
        var dir = new GameObject("DemoDirector").AddComponent<DemoDirector>();
        dir.player = player; dir.chest = chest; dir.furnace = furnace; dir.lamp = lamp; dir.bed = bed; dir.ui = ui; dir.rig = rig;
        dir.interactables = items; dir.sun = sun; dir.sideLamp = sideLamp; dir.shelf = shelf;

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        AssetDatabase.SaveAssets();
        Report.Add("scene saved " + ScenePath);
        return dir.gameObject;
    }

    // ---------------------------------------------------------------- interactable setup
    static PlayerAvatar BuildPlayer()
    {
        const string path = Art + "/Character/QPlayerMale_v006.fbx";
        var root = new GameObject("Player");
        var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
        model.transform.SetParent(root.transform, false);
        var anim = model.GetComponent<Animator>(); if (anim) Object.DestroyImmediate(anim);
        var av = root.AddComponent<PlayerAvatar>(); av.model = model;
        var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();
        av.idleClip = clips.FirstOrDefault(c => c.name.Contains("Idle"));
        av.walkClip = clips.FirstOrDefault(c => c.name.Contains("Walk"));
        Report.Add("character clips: " + string.Join(", ", clips.Select(c => $"{c.name} {c.length:0.00}s")));
        if (av.idleClip) av.idleClip.SampleAnimation(model, 0f);
        var b = WorldBounds(model);
        Report.Add($"character bounds size {b.size} (model_info height 1.447)");
        if (b.size.y > 2.5f || b.size.y < .8f) { model.transform.localScale *= 1.447f / b.size.y; Report.Add("character rescaled to 1.447 m"); }
        root.transform.position = new Vector3(0f, 0f, -.7f);
        // alchemy materials come from the bag itself (青靈草 ×2 + 淨水蓮 ×1 per batch, plus firewood)
        av.inventory = new List<ItemStack> { new ItemStack("青瓷罐", 1), new ItemStack("卷軸", 1), new ItemStack("青靈草", 4), new ItemStack("淨水蓮", 2), new ItemStack("松柴", 6) };
        return av;
    }

    static ChestStorage BuildChest(GameObject chestGo)
    {
        var t = chestGo.transform;
        var lidParts = Children(t).Where(c => c.name.StartsWith("Chest_Separate_Lid") || c.name.StartsWith("Lid_Metal_Strap")).ToList();
        var hinges = Children(t).Where(c => c.name.StartsWith("Lid_Hinge_Barrel")).ToList();
        var bodyParts = Children(t).Where(c => c.GetComponent<Renderer>() && !lidParts.Contains(c) && !c.name.StartsWith("Lid_Hinge")).Select(c => c.gameObject).ToList();
        var lidB = WorldBounds(lidParts.Select(c => c.gameObject));
        var bodyB = WorldBounds(bodyParts);
        Vector3 hingeW = hinges.Count > 0 ? WorldBounds(hinges.Select(c => c.gameObject)).center : new Vector3(lidB.center.x, lidB.min.y, lidB.center.z);
        // the FBX lid sits closed; "front" runs from the hinge line towards the body centre
        Vector3 frontDir = bodyB.center - hingeW; frontDir.y = 0; frontDir.Normalize();
        var pivot = new GameObject("Lid_Pivot").transform; pivot.SetParent(t, false);
        pivot.SetPositionAndRotation(hingeW, Quaternion.LookRotation(frontDir, Vector3.up));
        foreach (var c in lidParts) c.SetParent(pivot, true);

        // closed angle: the rotation about the hinge that lays the lid flattest over the body
        var verts = new List<Vector3>();
        foreach (var mf in pivot.GetComponentsInChildren<MeshFilter>())
        {
            if (!mf.sharedMesh || mf.name.Contains("_LOD1") || mf.name.Contains("_LOD2")) continue;
            var vs = mf.sharedMesh.vertices;
            for (int i = 0; i < vs.Length; i += 7) verts.Add(pivot.InverseTransformPoint(mf.transform.TransformPoint(vs[i])));
        }
        float best = 0f, bestH = float.MaxValue;
        for (float a = -180f; a <= 180f; a += .5f)
        {
            var q = Quaternion.AngleAxis(a, Vector3.right);
            float lo = float.MaxValue, hi = float.MinValue, cz = 0f;
            foreach (var v in verts) { var r = q * v; lo = Mathf.Min(lo, r.y); hi = Mathf.Max(hi, r.y); cz += r.z; }
            if (cz / Mathf.Max(1, verts.Count) <= 0f) continue;
            if (hi - lo < bestH) { bestH = hi - lo; best = a; }
        }
        var chest = chestGo.AddComponent<ChestStorage>();
        chest.lidPivot = pivot; chest.hingeAxis = Vector3.right; chest.lidRest = pivot.localRotation;   // the chest root carries an axis fix-up, so angles apply on top of the rest pose
        chest.closedAngle = best; chest.openAngle = best - 90f;   // lid stands upright at 90 deg (further would clip the wall behind)
        pivot.localRotation = chest.lidRest * Quaternion.AngleAxis(best, Vector3.right);
        Report.Add($"chest lid parts {lidParts.Count}, hinge barrels {hinges.Count}, closed angle {best:0.0} (lid thickness {bestH:0.000} m), open angle {chest.openAngle:0.0}");

        // stored items with a visual sit on the chest floor in two rows
        var bottom = Children(t).FirstOrDefault(c => c.name.StartsWith("Chest_Bottom"));
        float floorY = bottom ? WorldBounds(new[] { bottom.gameObject }).max.y : t.position.y + .22f;
        Vector3 rightW = Vector3.Cross(Vector3.up, frontDir);
        float width = Mathf.Abs(Vector3.Dot(bodyB.size, new Vector3(Mathf.Abs(rightW.x), 0, Mathf.Abs(rightW.z))));
        float depth = Mathf.Abs(Vector3.Dot(bodyB.size, new Vector3(Mathf.Abs(frontDir.x), 0, Mathf.Abs(frontDir.z))));
        float chestYaw = Quaternion.LookRotation(-frontDir).eulerAngles.y;   // item fronts face out of the chest's front
        var visuals = new (string name, GameObject go)[]
        {
            ("木匣", Place(TiPath("TI08a_KeepsakeBox"), "InChest_KeepsakeBox", 0, 0, 0, true)),
            ("藥罐", Place(TiPath("TI08d_MedicinePot"), "InChest_MedicinePot", 0, 0, 0, true)),
            ("青瓷罐", Place(TiPath("TI08c_CeladonJar"), "InChest_CeladonJar", 0, 0, 0, true)),
            ("卷軸", Place(TiPath("TI08b_PaperScroll"), "InChest_PaperScroll", 0, 0, 0, true)),
            ("青靈草", Prop(Art + "/Existing/SpiritHerbMature_v001.fbx", "InChest_Herb", .2f)),
            ("淨水蓮", Lotus("InChest_Lotus", .16f)),
            ("松柴", Prop(Art + "/Existing/FirewoodStack_v002.fbx", "InChest_Firewood", .26f)),
        };
        chest.itemNames = visuals.Select(v => v.name).ToArray(); chest.itemVisuals = new GameObject[visuals.Length];
        Vector3 c0 = new Vector3(bodyB.center.x, floorY + .002f, bodyB.center.z);
        for (int i = 0; i < visuals.Length; i++)
        {
            int row = i < 4 ? 0 : 1, n = row == 0 ? 4 : 3, col = row == 0 ? i : i - 4;
            float u = (col - (n - 1) * .5f) * width * .62f / n, v = (row == 0 ? .13f : -.14f) * depth;
            var g = visuals[i].go;
            var baseRot = g.transform.rotation;
            g.transform.SetPositionAndRotation(c0 + rightW * u + frontDir * v, Quaternion.Euler(0, chestYaw + 12f * i - 18f, 0) * baseRot);
            g.transform.SetParent(t, true);
            chest.itemVisuals[i] = g;
        }
        chest.capacity = 30;
        chest.contents = new List<ItemStack>
        {
            new ItemStack("木匣", 1), new ItemStack("藥罐", 1), new ItemStack("青靈草", 6), new ItemStack("淨水蓮", 3),
            new ItemStack("松柴", 99), new ItemStack("松柴", 37), new ItemStack("回春丹・凡品", 2),
        };
        chest.RefreshVisuals();
        chest.standPoint = Marker("Chest_Stand", new Vector3(2.95f, 0, .8f), chestGo.transform);   // off to the right so the close-up sees past the player
        chest.shotFocus = chestGo.transform.position + new Vector3(-.15f, -.18f, -.15f);   // low focus lifts the box above the storage panel
        chest.shotDistance = 3.0f; chest.shotYaw = -17f; chest.shotPitch = 68f; chest.shotFov = 38f;   // looks over the player's head; the player sits under the storage panel
        return chest;
    }

    /// Collection shelf: the 8 SOCKET_slot_N empties from the TI01 model, one hidden model per TI08 piece to copy from.
    static ShelfDisplay BuildShelf(GameObject go)
    {
        var d = go.AddComponent<ShelfDisplay>();
        for (int i = 0; i < Shelf.Slots; i++)
        {
            d.sockets[i] = Children(go.transform).FirstOrDefault(c => c.name == "SOCKET_slot_" + (i + 1)) ?? FindChild(go.transform, "SOCKET_slot_" + (i + 1));
            if (d.sockets[i] == null) Report.Add("missing socket slot " + (i + 1));
        }
        var pieces = new[] { ("木匣", "TI08a_KeepsakeBox"), ("卷軸", "TI08b_PaperScroll"), ("青瓷罐", "TI08c_CeladonJar"), ("藥罐", "TI08d_MedicinePot") };
        var root = new GameObject("Shelf_PieceTemplates");
        d.pieceNames = pieces.Select(p => p.Item1).ToArray();
        d.pieceTemplates = pieces.Select(p =>
        {
            var g = Place(TiPath(p.Item2), "Piece_" + p.Item2, 0, 0, 0, true);
            g.transform.SetParent(root.transform, true); g.SetActive(false);
            return g;
        }).ToArray();
        d.startSlots[1] = "木匣";                                        // one old piece already up when the house is yours
        d.standPoint = Marker("Shelf_Stand", new Vector3(2.35f, 0, .45f), go.transform);
        d.shotFocus = go.transform.position + new Vector3(-.25f, .95f, .55f);   // left of the shelf, so the shelf sits right of the panel
        d.shotDistance = 2.9f; d.shotYaw = 70f; d.shotPitch = 10f; d.shotFov = 50f;
        return d;
    }

    /// Existing (non-TI) prop scaled so its largest extent is `size` metres; pivot stays at the base.
    static GameObject Prop(string path, string name, float size)
    {
        var g = Place(path, name, 0, 0, 0, false);
        var b = WorldBounds(g);
        float m = Mathf.Max(b.size.x, b.size.y, b.size.z);
        if (m > 1e-4f) g.transform.localScale *= size / m;
        foreach (var r in g.GetComponentsInChildren<Renderer>()) if (r.name.Contains("_LOD1") || r.name.Contains("_LOD2")) r.enabled = false;
        return g;
    }

    /// 淨水蓮 has no model in the library yet: a small primitive stand-in (leaf pad, eight petals, seed head).
    static GameObject Lotus(string name, float size)
    {
        var root = new GameObject(name);
        var pad = GameObject.CreatePrimitive(PrimitiveType.Cylinder); pad.name = "Lotus_Pad";
        pad.transform.SetParent(root.transform, false); pad.transform.localScale = new Vector3(1f, .02f, 1f); pad.transform.localPosition = new Vector3(0, .02f, 0);
        pad.GetComponent<Renderer>().sharedMaterial = Plain("Lotus_Leaf", new Color(.27f, .45f, .26f), .35f);
        var petalM = Plain("Lotus_Petal", new Color(.95f, .86f, .88f), .45f);
        for (int ring = 0; ring < 2; ring++)
            for (int i = 0; i < 8; i++)
            {
                var p = GameObject.CreatePrimitive(PrimitiveType.Sphere); p.name = "Lotus_Petal";
                p.transform.SetParent(root.transform, false);
                float a = i * 45f + ring * 22.5f, tilt = ring == 0 ? 35f : 60f, r = ring == 0 ? .2f : .12f;
                p.transform.localRotation = Quaternion.Euler(0, a, 0) * Quaternion.Euler(-tilt, 0, 0);
                p.transform.localPosition = Quaternion.Euler(0, a, 0) * new Vector3(0, .12f + ring * .05f, r);
                p.transform.localScale = new Vector3(.16f, .05f, .34f) * (ring == 0 ? 1f : .8f);
                p.GetComponent<Renderer>().sharedMaterial = petalM;
            }
        var seed = GameObject.CreatePrimitive(PrimitiveType.Cylinder); seed.name = "Lotus_Seedhead";
        seed.transform.SetParent(root.transform, false); seed.transform.localScale = new Vector3(.12f, .03f, .12f); seed.transform.localPosition = new Vector3(0, .2f, 0);
        seed.GetComponent<Renderer>().sharedMaterial = Plain("Lotus_Seed", new Color(.85f, .72f, .30f), .3f);
        foreach (var col in root.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(col);
        root.transform.localScale = Vector3.one * size;
        return root;
    }

    static FurnaceFire BuildFurnace(GameObject go)
    {
        var f = go.AddComponent<FurnaceFire>();
        f.fireObjects = Children(go.transform).Where(c => c.name.Contains("_Fire_LOD")).Select(c => c.gameObject).ToArray();
        f.emissiveMats = OwnMaterials(go);
        f.mouth = FindChild(go.transform, "SOCKET_fire_light") ?? go.transform;
        f.mouthOutward = go.transform.forward;
        f.lidParts = Children(go.transform).Where(c => c.name.Contains("_Lid_LOD")).ToArray();
        f.lidOpenOffset = Vector3.up * .2f - go.transform.forward * .1f;
        f.lidTiltAxis = go.transform.right;
        var lg = new GameObject("Fire_Light"); lg.transform.SetParent(f.mouth, false); lg.transform.localPosition = Vector3.zero;
        lg.transform.position += go.transform.forward * .12f;
        var l = lg.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(1f, .55f, .22f); l.range = 4.5f; l.shadows = LightShadows.Soft; l.enabled = false;
        f.fireLight = l;
        var log = GameObject.CreatePrimitive(PrimitiveType.Cylinder); log.name = "Firewood_Log";
        Object.DestroyImmediate(log.GetComponent<Collider>());
        log.transform.SetParent(go.transform, false); log.transform.localScale = new Vector3(.065f, .12f, .065f);
        log.GetComponent<Renderer>().sharedMaterial = Plain("Firewood_Bark", new Color(.23f, .14f, .07f), .1f);
        log.SetActive(false); f.logPrefab = log;
        var water = GameObject.CreatePrimitive(PrimitiveType.Sphere); water.name = "Water_Ladle";
        Object.DestroyImmediate(water.GetComponent<Collider>());
        water.transform.SetParent(go.transform, false); water.transform.localScale = new Vector3(.08f, .05f, .08f);
        water.GetComponent<Renderer>().sharedMaterial = Plain("Water_Drop", new Color(.45f, .68f, .86f), .9f);
        water.SetActive(false); f.waterPrefab = water;
        var herb = Prop(Art + "/Existing/SpiritHerbMature_v001.fbx", "Herb_Charge", .16f); herb.transform.SetParent(go.transform, true); herb.SetActive(false); f.herbPrefab = herb;
        var pill = Prop(Art + "/Existing/QPillBottle_v002.fbx", "Pill_Bottle", .14f); pill.transform.SetParent(go.transform, true); pill.SetActive(false); f.pillPrefab = pill;
        f.standPoint = Marker("Furnace_Stand", new Vector3(2.2f, 0, -1.2f), go.transform);
        // close-up from the room side, furnace on the left third (the alchemy panel takes the right)
        float yaw = 100f; Vector3 right = Quaternion.Euler(0, yaw, 0) * Vector3.right;
        f.shotFocus = go.transform.position + Vector3.up * .5f + right * .38f;
        f.shotFocus.z = Mathf.Max(f.shotFocus.z, -2.2f);
        f.shotDistance = 2.7f; f.shotYaw = yaw; f.shotPitch = 24f; f.shotFov = 42f;
        foreach (var o in f.fireObjects) o.SetActive(false);
        Report.Add($"furnace fire objects {f.fireObjects.Length}, lid parts {f.lidParts.Length}, mouth {(f.mouth != go.transform)}");
        return f;
    }

    static PaperLamp BuildLamp(GameObject go, bool interactive)
    {
        var lamp = go.AddComponent<PaperLamp>();
        lamp.emissiveMats = OwnMaterials(go);
        var sock = FindChild(go.transform, "SOCKET_lamp_light") ?? go.transform;
        var lg = new GameObject("Lamp_Light"); lg.transform.SetParent(sock, false);
        var l = lg.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(1f, .70f, .42f); l.range = 5f; l.shadows = LightShadows.Soft; l.enabled = false;
        lamp.lampLight = l;
        if (interactive)
        {
            lamp.standPoint = Marker("Lamp_Stand", new Vector3(-2.3f, 0, -.25f), go.transform);
            // from the south-east so the player stands to the right of the lamp, not in front of it
            lamp.shotFocus = go.transform.position + Vector3.up * 1.0f; lamp.shotDistance = 2.2f; lamp.shotYaw = -60f; lamp.shotPitch = 16f; lamp.shotFov = 46f;
        }
        return lamp;
    }

    static BedRest BuildBed(GameObject go, PlayerAvatar player)
    {
        var bed = go.AddComponent<BedRest>();
        var t = go.transform;
        var pillow = Children(t).FirstOrDefault(c => c.name.StartsWith("Pillow"));
        var folded = Children(t).FirstOrDefault(c => c.name.StartsWith("Folded_Quilt"));
        var mattress = Children(t).FirstOrDefault(c => c.name.StartsWith("Woven_Mattress"));
        var bb = WorldBounds(new[] { go });
        Vector3 head = pillow ? pillow.position - bb.center : t.forward * -1f; head.y = 0; head.Normalize();
        Vector3 side = Vector3.Cross(Vector3.up, head);
        var mb = mattress ? WorldBounds(new[] { mattress.gameObject }) : bb;
        float top = mattress ? mb.max.y : bb.min.y + .5f;              // lie on the mattress, not on the folded quilt
        // avatar local bounds (Idle frame): back of the body is its most negative local z
        var pb = LocalBounds(player.model.transform, player.transform);
        bed.lieRotation = Quaternion.LookRotation(Vector3.up, head);
        Vector3 centre = new Vector3(mb.center.x, 0, mb.center.z);
        bed.liePosition = centre - head * (pb.size.y * .5f) + head * .08f + Vector3.up * (top - pb.min.z + .005f);
        bed.standPoint = Marker("Bed_Stand", new Vector3(-1.75f, 0, 1.0f), t);   // bedside, room side
        bed.headDir = head; bed.mattressTop = top;
        bed.halfWidth = Mathf.Abs(Vector3.Dot(mb.size, new Vector3(Mathf.Abs(side.x), 0, Mathf.Abs(side.z)))) * .5f;
        bed.sideOut = Vector3.Dot(bed.standPoint.position - mb.center, side) >= 0f ? side : -side;
        bed.foldedQuilt = folded ? folded.gameObject : null;
        bed.quiltPivot = BuildQuilt(player, bed, head, side, mb, top, folded);
        Vector3 bc = new Vector3(mb.center.x, top, mb.center.z);
        bed.shotFocus = bc + Vector3.up * .15f + head * .25f;
        bed.shotDistance = 2.4f; bed.shotYaw = Quaternion.LookRotation(head).eulerAngles.y - 75f; bed.shotPitch = 42f; bed.shotFov = 46f;   // from the room side, looking across the bed
        Report.Add($"bed mattress top {top:0.000}, head dir {head}, avatar local bounds {pb.min}..{pb.max}");
        return bed;
    }

    /// Spread quilt shaped over the lying avatar: a height field from the baked lying pose, from the foot of the bed
    /// up to the shoulders (head left uncovered), draping over the mattress sides and foot. Pivot on the foot edge.
    static Transform BuildQuilt(PlayerAvatar player, BedRest bed, Vector3 head, Vector3 side, Bounds mb, float top, Transform folded)
    {
        var pt = player.transform; Vector3 p0 = pt.position; Quaternion r0 = pt.rotation;
        pt.SetPositionAndRotation(bed.liePosition, bed.lieRotation);
        // body points in bed space: x across, y up, z along head
        float halfLen = Mathf.Abs(Vector3.Dot(mb.size, new Vector3(Mathf.Abs(head.x), 0, Mathf.Abs(head.z)))) * .5f;
        float halfW = Mathf.Abs(Vector3.Dot(mb.size, new Vector3(Mathf.Abs(side.x), 0, Mathf.Abs(side.z)))) * .5f;
        Vector3 c = new Vector3(mb.center.x, 0, mb.center.z);
        Vector3 foot = c - head * halfLen;
        var pts = new List<Vector3>();
        foreach (var smr in player.model.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            var m = new Mesh(); smr.BakeMesh(m, true);
            foreach (var v in m.vertices) { var w = smr.transform.TransformPoint(v) - foot; pts.Add(new Vector3(Vector3.Dot(w, side), w.y, Vector3.Dot(w, head))); }
            Object.DestroyImmediate(m);
        }
        // shoulder line: the neck bone if the rig has one, else 58 % up a chibi body
        var neck = player.model.GetComponentsInChildren<Transform>().FirstOrDefault(b => b.name.ToLower().Contains("neck"));
        float zMin = pts.Min(p => p.z), zMax = pts.Max(p => p.z);
        float zNeck = neck ? Vector3.Dot(neck.position - foot, head) - .03f : zMin + (zMax - zMin) * .58f;
        pt.SetPositionAndRotation(p0, r0);

        const int NU = 26, NV = 40;                 // across, along
        float over = .09f, len = zNeck + over;      // hangs .09 m past the foot edge
        float wTot = 2f * (halfW + over);
        var h = new float[NU + 1, NV + 1];
        float cellU = wTot / NU, cellV = len / NV;
        for (int i = 0; i <= NU; i++)
            for (int j = 0; j <= NV; j++)
            {
                float x = -halfW - over + i * cellU, z = -over + j * cellV;
                float body = top;
                foreach (var p in pts) if (Mathf.Abs(p.x - x) < cellU * 1.5f && Mathf.Abs(p.z - z) < cellV * 1.5f && p.y > body) body = p.y;
                h[i, j] = body + .05f;
            }
        // soften the shape like cloth: dilate then blur
        for (int pass = 0; pass < 10; pass++)
        {
            var n = (float[,])h.Clone();
            for (int i = 0; i <= NU; i++)
                for (int j = 0; j <= NV; j++)
                {
                    float s = 0; int k = 0;
                    for (int di = -1; di <= 1; di++) for (int dj = -1; dj <= 1; dj++)
                    {
                        int a = Mathf.Clamp(i + di, 0, NU), b = Mathf.Clamp(j + dj, 0, NV);
                        s += pass == 0 ? 0 : h[a, b]; k++;
                        if (pass == 0) n[i, j] = Mathf.Max(n[i, j], h[a, b]);
                    }
                    if (pass > 0) n[i, j] = s / k;
                }
            h = n;
        }
        // drape past the mattress edges and the foot
        var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        for (int j = 0; j <= NV; j++)
            for (int i = 0; i <= NU; i++)
            {
                float x = -halfW - over + i * cellU, z = -over + j * cellV;
                float y = Mathf.Max(h[i, j], top + .025f);
                float outX = Mathf.Abs(x) - halfW, outZ = -z;
                if (outX > 0) y -= outX * 2.3f;
                if (outZ > 0) y -= outZ * 2.3f;
                verts.Add(new Vector3(x, y - top, z)); uvs.Add(new Vector2(x * 1.6f, z * 1.6f));
            }
        int W = NU + 1, top0 = 0;
        for (int j = 0; j < NV; j++)
            for (int i = 0; i < NU; i++)
            {
                int a = top0 + j * W + i, b = a + 1, cc = a + W, d = cc + 1;
                tris.AddRange(new[] { a, cc, b, b, cc, d });
            }
        int bot0 = verts.Count;                     // underside, 1.5 cm lower, wound the other way
        for (int k = 0; k < bot0; k++) { verts.Add(verts[k] - Vector3.up * .015f); uvs.Add(uvs[k]); }
        for (int j = 0; j < NV; j++)
            for (int i = 0; i < NU; i++)
            {
                int a = bot0 + j * W + i, b = a + 1, cc = a + W, d = cc + 1;
                tris.AddRange(new[] { a, b, cc, b, d, cc });
            }
        var mesh = new Mesh { name = "Bed_Quilt_Spread" };
        mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        Directory.CreateDirectory(Gen + "/Meshes");
        AssetDatabase.DeleteAsset(Gen + "/Meshes/Bed_Quilt_Spread.asset");
        AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/Bed_Quilt_Spread.asset");

        var go = new GameObject("Bed_Quilt_Spread");
        go.transform.SetPositionAndRotation(new Vector3(foot.x, top, foot.z), Quaternion.LookRotation(head, Vector3.up));   // pivot on the mattress top so unrolling stays on the bed
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var mr = go.AddComponent<MeshRenderer>();
        var fr = folded ? folded.GetComponentInChildren<Renderer>() : null;
        // matte cloth: the folded quilt's colour / texture without its gloss
        AssetDatabase.DeleteAsset(Gen + "/Materials/Quilt_Spread_Matte.mat");
        var cloth = fr ? new Material(fr.sharedMaterial) : new Material(Shader.Find("Standard")) { color = new Color(.25f, .42f, .40f) };
        cloth.DisableKeyword("_METALLICGLOSSMAP"); cloth.SetTexture("_MetallicGlossMap", null);
        cloth.SetFloat("_Metallic", 0f); cloth.SetFloat("_Glossiness", .06f); cloth.SetFloat("_GlossMapScale", .06f);
        AssetDatabase.CreateAsset(cloth, Gen + "/Materials/Quilt_Spread_Matte.mat");
        mr.sharedMaterial = cloth;
        go.SetActive(false);
        Report.Add($"quilt: {NU}x{NV} grid, length {len:0.00} m to the shoulders (neck bone {(neck ? neck.name : "none")}), width {wTot:0.00} m");
        return go.transform;
    }

    /// 256 px thumbnail of a prop (transparent background), saved under Generated/Icons/<key>.png. Destroys `go`.
    static Texture2D RenderIcon(string iconKey, GameObject go)
    {
        const int S = 256;
        Directory.CreateDirectory(Gen + "/Icons");
        string path = $"{Gen}/Icons/{iconKey}.png";
        go.transform.SetPositionAndRotation(new Vector3(0, -60, 0), Quaternion.Euler(0, 200f, 0) * go.transform.rotation);
        go.SetActive(true);
        foreach (var r in go.GetComponentsInChildren<Renderer>()) if (r.name.Contains("_LOD1") || r.name.Contains("_LOD2")) r.enabled = false;
        var b = WorldBounds(go);
        var camGo = new GameObject("Icon_Camera"); var cam = camGo.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0, 0, 0, 0);
        cam.fieldOfView = 24f; cam.nearClipPlane = .001f; cam.farClipPlane = 10f;
        Vector3 dir = new Vector3(0, .55f, -1f).normalized;
        float dist = b.extents.magnitude / Mathf.Sin(cam.fieldOfView * .5f * Mathf.Deg2Rad) * 1.02f;
        camGo.transform.position = b.center + dir * dist; camGo.transform.LookAt(b.center);
        var keyGo = new GameObject("Icon_Key"); var key = keyGo.AddComponent<Light>(); key.type = LightType.Directional; key.intensity = 1.25f;
        key.color = new Color(1f, .95f, .88f); keyGo.transform.rotation = Quaternion.Euler(40f, 150f, 0f);
        var rt = new RenderTexture(S, S, 24, RenderTextureFormat.ARGB32) { antiAliasing = 8 };
        cam.targetTexture = rt; cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(S, S, TextureFormat.RGBA32, false); tex.ReadPixels(new Rect(0, 0, S, S), 0, 0); tex.Apply();
        RenderTexture.active = null;
        File.WriteAllBytes(path, tex.EncodeToPNG());
        Object.DestroyImmediate(tex); cam.targetTexture = null; rt.Release();
        Object.DestroyImmediate(camGo); Object.DestroyImmediate(keyGo); Object.DestroyImmediate(go);
        AssetDatabase.ImportAsset(path);
        var ti = (TextureImporter)AssetImporter.GetAtPath(path);
        ti.alphaIsTransparency = true; ti.mipmapEnabled = false; ti.SaveAndReimport();
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    // ---------------------------------------------------------------- placement & materials
    static string TiPath(string id) => $"{Art}/TI18/{id}/{id}_v001.fbx";

    static GameObject Place(string path, string name, float x, float z, float yaw, bool tiMaterials)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (asset == null) { Report.Add("MISSING " + path); return new GameObject(name + "_MISSING"); }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        go.name = name; go.transform.SetPositionAndRotation(new Vector3(x, 0, z), Quaternion.Euler(0, yaw, 0) * asset.transform.rotation);   // keep the importer's axis fix-up
        if (tiMaterials)
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                r.sharedMaterials = r.sharedMaterials.Select(m => m ? TiMaterial(m.name) : m).ToArray();
        return go;
    }

    /// Per-instance copies so lamps / furnace can drive emission independently.
    static Material[] OwnMaterials(GameObject go)
    {
        var map = new Dictionary<Material, Material>();
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            r.sharedMaterials = r.sharedMaterials.Select(m =>
            {
                if (m == null) return m;
                if (!map.TryGetValue(m, out var c)) { c = new Material(m) { name = m.name + "_" + go.name }; map[m] = c; }
                return c;
            }).ToArray();
        return map.Values.Where(m => m.IsKeywordEnabled("_EMISSION")).ToArray();
    }

    static readonly Dictionary<string, Material> matCache = new Dictionary<string, Material>();

    static Material TiMaterial(string fbxName)
    {
        string name = fbxName.Replace(" (Instance)", "");
        if (matCache.TryGetValue(name, out var cached) && cached) return cached;
        string path = $"{Gen}/Materials/{name}.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null) { mat = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(mat, path); }
        // M_<ID>_<Slot>; the ID is the folder name under Art/TI18
        string id = Directory.GetDirectories(Art + "/TI18").Select(Path.GetFileName).FirstOrDefault(d => name.StartsWith("M_" + d + "_"));
        if (id == null) { Report.Add("unmapped material " + name); return mat; }
        string slot = name.Substring(("M_" + id + "_").Length), dirp = $"{Art}/TI18/{id}/";
        var own = Directory.GetFiles(dirp, $"{id}_{slot}*.png").Select(p => p.Replace('\\', '/')).FirstOrDefault();
        Texture2D T(string suffix) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{dirp}{id}_{suffix}.png");
        if (own != null)
        {
            mat.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(own));
            mat.SetFloat("_Glossiness", .12f); mat.SetFloat("_Metallic", 0f);
        }
        else
        {
            mat.SetTexture("_MainTex", T("BaseColor"));
            var ms = T("MetallicSmoothness");
            if (ms) { mat.SetTexture("_MetallicGlossMap", ms); mat.EnableKeyword("_METALLICGLOSSMAP"); mat.SetFloat("_GlossMapScale", 1f); }
            var n = T("Normal");
            if (n) { mat.SetTexture("_BumpMap", n); mat.EnableKeyword("_NORMALMAP"); }
            var e = T("Emission");
            if (e)
            {
                mat.SetTexture("_EmissionMap", e); mat.EnableKeyword("_EMISSION"); mat.SetColor("_EmissionColor", Color.black);
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
        }
        EditorUtility.SetDirty(mat);
        matCache[name] = mat;
        return mat;
    }

    static Material Plain(string name, Color c, float gloss)
    {
        string path = $"{Gen}/Materials/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(m, path); }
        m.color = c; m.SetFloat("_Glossiness", gloss); EditorUtility.SetDirty(m);
        return m;
    }

    static GameObject Slab(GameObject parent, string name, Vector3 pos, Vector3 size, Material m)
    {
        var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = name;
        g.transform.SetParent(parent.transform, false); g.transform.localPosition = pos; g.transform.localScale = size;
        g.GetComponent<Renderer>().sharedMaterial = m;
        return g;
    }

    static Transform Marker(string name, Vector3 pos, Transform parent)
    {
        var g = new GameObject(name); g.transform.position = pos; g.transform.SetParent(parent, true); return g.transform;
    }

    // ---------------------------------------------------------------- helpers
    static IEnumerable<Transform> Children(Transform t) => t.GetComponentsInChildren<Transform>(true).Where(c => c != t);
    static Transform FindChild(Transform t, string prefix) => Children(t).FirstOrDefault(c => c.name.StartsWith(prefix));

    public static Bounds WorldBounds(IEnumerable<GameObject> gos)
    {
        bool any = false; var b = new Bounds();
        foreach (var go in gos)
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                if (r is SkinnedMeshRenderer smr) { var m = new Mesh(); smr.BakeMesh(m, true); var w = TransformBounds(m.bounds, smr.transform); if (!any) b = w; else b.Encapsulate(w); any = true; Object.DestroyImmediate(m); continue; }
                if (r.name.Contains("_LOD1") || r.name.Contains("_LOD2")) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
        return b;
    }
    static Bounds WorldBounds(GameObject go) => WorldBounds(new[] { go });

    static Bounds TransformBounds(Bounds lb, Transform t)
    {
        var b = new Bounds(t.TransformPoint(lb.center), Vector3.zero);
        for (int i = 0; i < 8; i++)
            b.Encapsulate(t.TransformPoint(lb.center + Vector3.Scale(lb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))));
        return b;
    }

    /// Bounds of a skinned model in the space of `space` (baked at the current pose).
    static Bounds LocalBounds(Transform model, Transform space)
    {
        bool any = false; var b = new Bounds();
        foreach (var smr in model.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            var m = new Mesh(); smr.BakeMesh(m, true);
            foreach (var v in m.vertices)
            {
                var p = space.InverseTransformPoint(smr.transform.TransformPoint(v));
                if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
            }
            Object.DestroyImmediate(m);
        }
        foreach (var mr in model.GetComponentsInChildren<MeshRenderer>())
        {
            var mf = mr.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
            foreach (var v in mf.sharedMesh.vertices)
            {
                var p = space.InverseTransformPoint(mr.transform.TransformPoint(v));
                if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
            }
        }
        return b;
    }

    // ---------------------------------------------------------------- importers
    static void ConfigureImporters()
    {
        AssetDatabase.Refresh();
        foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Art }))
        {
            var p = AssetDatabase.GUIDToAssetPath(guid); var ti = (TextureImporter)AssetImporter.GetAtPath(p);
            bool changed = false;
            if (p.EndsWith("_Normal.png") && ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; changed = true; }
            bool linear = p.EndsWith("_MetallicSmoothness.png") || p.EndsWith("_Metallic.png") || p.EndsWith("_Roughness.png");
            if (linear && ti.sRGBTexture) { ti.sRGBTexture = false; changed = true; }
            if (ti.maxTextureSize != 4096) { ti.maxTextureSize = 4096; changed = true; }
            if (changed) ti.SaveAndReimport();
        }
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Art }))
        {
            var p = AssetDatabase.GUIDToAssetPath(guid); var mi = (ModelImporter)AssetImporter.GetAtPath(p);
            bool character = p.Contains("/Character/"); bool changed = false;
            if (mi.importCameras || mi.importLights) { mi.importCameras = false; mi.importLights = false; changed = true; }
            if (character)
            {
                if (mi.animationType != ModelImporterAnimationType.Generic) { mi.animationType = ModelImporterAnimationType.Generic; changed = true; }
                var clips = mi.defaultClipAnimations;
                if (mi.clipAnimations.Length == 0 && clips.Length > 0)
                {
                    foreach (var c in clips) { c.loopTime = true; c.name = c.name.Contains("|") ? c.name.Split('|').Last() : c.name; }
                    mi.clipAnimations = clips; changed = true;
                }
            }
            else if (mi.importAnimation) { mi.importAnimation = false; changed = true; }
            if (changed) mi.SaveAndReimport();
        }
    }
}
