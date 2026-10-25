using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;

namespace QingxiWorld
{
    // Local first-person walk-through of the integrated Qingxi world (Play mode in the Editor). Uses the game's walk speed
    // (4 m/s), a CharacterController against the same simplified colliders the route test used, and registers the baked
    // rabbit NavMesh so the rabbit stand-ins can flee. Not the networked FishNet Cultivator; nothing is sent to the API.
    [RequireComponent(typeof(CharacterController))]
    public sealed class QingxiFirstPerson : MonoBehaviour
    {
        public static QingxiFirstPerson Current { get; private set; }
        public Camera cam; public GameObject body; public NavMeshData rabbitNavMesh;
        public float walkSpeed = 4, runSpeed = 7, eyeHeight = 1.2f, lookSensitivity = .1f, gravity = -20, jumpSpeed = 5.5f;
        public string[] spotNames; public Vector3[] spotPositions; public float[] spotYaws;
        public Transform huntRoot; public string[] zoneLabels; public Vector4[] zoneRects;   // hunt-local centre x, z, width, depth
        public Transform[] pointsOfInterest;

        CharacterController cc; float yaw, pitch, vy, stopwatch; bool third = true, help = true; NavMeshDataInstance nav;
        readonly List<string> log = new List<string>(); readonly HashSet<string> reached = new HashSet<string>();
        GUIStyle box, small; GameObject[] overlays = new GameObject[0]; bool showOverlays;

        void OnEnable() { Current = this; if (rabbitNavMesh != null) nav = NavMesh.AddNavMeshData(rabbitNavMesh); }
        void OnDisable() { if (Current == this) Current = null; if (nav.valid) nav.Remove(); }
        void Start()
        {
            cc = GetComponent<CharacterController>(); yaw = transform.eulerAngles.y; Lock(true); ApplyView();
            // route-test lines and NavMesh previews start hidden in Play mode; L shows them
            overlays = new[] { "RouteTest_Lines", "NavMeshPreview_Player", "NavMeshPreview_Rabbit" }.Select(GameObject.Find).Where(g => g != null).ToArray();
            SetOverlays(false);
            Log("出發：" + Zone());
        }
        void SetOverlays(bool on) { showOverlays = on; foreach (var g in overlays) g.SetActive(on); }
        void Lock(bool on) { Cursor.lockState = on ? CursorLockMode.Locked : CursorLockMode.None; Cursor.visible = !on; }
        void ApplyView() { if (body != null) foreach (var r in body.GetComponentsInChildren<Renderer>()) r.enabled = third; }

        void Update()
        {
            var kb = Keyboard.current; var mouse = Mouse.current; if (kb == null || mouse == null) return;
            if (kb.escapeKey.wasPressedThisFrame) Lock(false);
            if (mouse.leftButton.wasPressedThisFrame && Cursor.lockState != CursorLockMode.Locked) Lock(true);
            if (kb.vKey.wasPressedThisFrame) { third = !third; ApplyView(); }
            if (kb.hKey.wasPressedThisFrame) help = !help;
            if (kb.lKey.wasPressedThisFrame) { SetOverlays(!showOverlays); Log(showOverlays ? "顯示測試路線與導航網格" : "隱藏測試路線與導航網格"); }
            for (int i = 0; i < spotPositions.Length && i < 9; i++)
                if (kb[(Key)((int)Key.Digit1 + i)].wasPressedThisFrame) Teleport(i);
            if (kb.fKey.wasPressedThisFrame)
            {
                var r = FindObjectsByType<QingxiRabbit>(FindObjectsSortMode.None).FirstOrDefault(x => x.TryCatch(transform.position, 2.2f));
                Log(r != null ? "抓到 " + r.spawnName + "（示意）。90 秒後在原出生點重生" : "附近 2.2 m 內沒有兔子");
            }
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                var d = mouse.delta.ReadValue(); yaw += d.x * lookSensitivity; pitch = Mathf.Clamp(pitch - d.y * lookSensitivity, -80, 80);
            }
            transform.rotation = Quaternion.Euler(0, yaw, 0);
            var input = new Vector2((kb.dKey.isPressed ? 1 : 0) - (kb.aKey.isPressed ? 1 : 0), (kb.wKey.isPressed ? 1 : 0) - (kb.sKey.isPressed ? 1 : 0));
            input = Vector2.ClampMagnitude(input, 1);
            float speed = kb.leftShiftKey.isPressed ? runSpeed : walkSpeed;
            if (cc.isGrounded) { vy = -2; if (kb.spaceKey.wasPressedThisFrame) vy = jumpSpeed; } else vy = Mathf.Max(-30, vy + gravity * Time.deltaTime);
            var move = transform.TransformDirection(new Vector3(input.x, 0, input.y)) * speed;
            cc.Move((move + Vector3.up * vy) * Time.deltaTime);
            if (input.sqrMagnitude > 0) stopwatch += Time.deltaTime;
            if (transform.position.y < -40) Teleport(0);
            UpdateCamera();
            foreach (var p in pointsOfInterest ?? new Transform[0])
                if (p != null && !reached.Contains(p.name) && (p.name.StartsWith("TrailClue") || p.name.StartsWith("HerbNode") || p.name.StartsWith("Merchant") || p.name.StartsWith("SafeReturn"))
                    && Vector3.Distance(Flat(p.position), Flat(transform.position)) < 3) { reached.Add(p.name); Log("到達 " + p.name + "：走了 " + stopwatch.ToString("0.0") + " 秒"); }
        }
        void UpdateCamera()
        {
            var eye = transform.position + Vector3.up * eyeHeight; var rot = Quaternion.Euler(pitch, yaw, 0);
            if (!third) { cam.transform.SetPositionAndRotation(eye, rot); return; }
            var back = rot * Vector3.back; float dist = 5f;
            if (Physics.SphereCast(eye, .2f, back, out var hit, dist, ~0, QueryTriggerInteraction.Ignore) && hit.collider.gameObject != gameObject) dist = Mathf.Max(.6f, hit.distance - .1f);
            cam.transform.SetPositionAndRotation(eye + back * dist, rot);
        }
        public void Teleport(int i)
        {
            cc.enabled = false; transform.position = spotPositions[i] + Vector3.up * .05f; cc.enabled = true;
            yaw = spotYaws[i]; pitch = 0; vy = 0; stopwatch = 0; reached.Clear(); Log("傳送到 " + spotNames[i] + "，計時歸零");
        }
        void Log(string s) { log.Add(s); if (log.Count > 5) log.RemoveAt(0); }
        string Zone()
        {
            if (huntRoot == null) return "青溪小鎮";
            var l = huntRoot.InverseTransformPoint(transform.position);
            if (l.x < 0 || l.x > 220 || l.z < 0 || l.z > 160) return "青溪小鎮";
            for (int i = 0; i < zoneRects.Length; i++)
            { var z = zoneRects[i]; if (Mathf.Abs(l.x - z.x) <= z.z / 2 && Mathf.Abs(l.z - z.y) <= z.w / 2) return "狩獵區・" + zoneLabels[i]; }
            return "狩獵區";
        }
        static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);

        void OnGUI()
        {
            if (box == null) { box = new GUIStyle(GUI.skin.box) { fontSize = 18, alignment = TextAnchor.UpperLeft, wordWrap = true }; small = new GUIStyle(box) { fontSize = 15 }; }
            var near = (pointsOfInterest ?? new Transform[0]).Where(p => p != null).Select(p => (p.name, d: Vector3.Distance(p.position, transform.position))).OrderBy(x => x.d).FirstOrDefault();
            var rabbits = FindObjectsByType<QingxiRabbit>(FindObjectsSortMode.None);
            var closeRabbit = rabbits.Where(r => !r.IsCaught).Select(r => (r.spawnName, d: Vector3.Distance(r.transform.position, transform.position))).OrderBy(x => x.d).FirstOrDefault();
            var caught = rabbits.Where(r => r.IsCaught).Select(r => r.spawnName + " " + r.RespawnIn.ToString("0") + " 秒").ToArray();
            string hud = Zone() + "　｜　" + (third ? "第三人稱" : "第一人稱") + "　｜　計時 " + stopwatch.ToString("0.0") + " 秒\n"
                + (near.name != null && near.d < 40 ? "最近標記：" + near.name + "　" + near.d.ToString("0") + " m\n" : "")
                + (closeRabbit.spawnName != null && closeRabbit.d < 30 ? "最近山兔：" + closeRabbit.spawnName + "　" + closeRabbit.d.ToString("0.0") + " m" + (closeRabbit.d < 2.2f ? "　［F 抓兔子］" : "") + "\n" : "")
                + (caught.Length > 0 ? "等待重生：" + string.Join("、", caught) + "\n" : "")
                + string.Join("\n", log);
            GUI.Box(new Rect(12, 12, 560, 34 + 24 * (3 + log.Count)), hud, box);
            if (help) GUI.Box(new Rect(12, Screen.height - 206, 560, 194),
                "WASD 走路（4 m/s）　Shift 跑　空白鍵 跳　滑鼠 看\nV 切換第一／第三人稱　F 抓兔子　L 測試路線　H 隱藏說明\nEsc 放開滑鼠，點畫面再鎖定\n傳送：" +
                string.Join("　", spotNames.Select((n, i) => (i + 1) + " " + n)) + "\n本機演練：不是連線版角色，不會寫入伺服器。", small);
            GUI.Label(new Rect(Screen.width / 2 - 4, Screen.height / 2 - 12, 20, 24), third ? "" : "+");
        }
    }
}
