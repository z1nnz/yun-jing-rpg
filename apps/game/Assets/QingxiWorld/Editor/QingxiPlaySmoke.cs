// Batch Play-mode smoke test of the first-person walk-through: teleports, walks with the CharacterController, walks up to
// rabbit A01 and checks that it flees along the rabbit NavMesh, then catches it. Writes artifacts/qingxi-world/play_smoke.txt and quits.
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace QingxiWorld.Editor
{
    [InitializeOnLoad]
    public static class QingxiPlaySmoke
    {
        const string Key = "QingxiPlaySmoke";
        static QingxiPlaySmoke() { if (SessionState.GetBool(Key, false)) EditorApplication.update += Tick; }
        public static void Run()
        {
            EditorSceneManager.OpenScene("Assets/QingxiWorld/Generated/QingxiWorld.unity");
            SessionState.SetBool(Key, true); SessionState.SetString(Key + "Log", ""); EditorApplication.update += Tick; EditorApplication.EnterPlaymode();
        }
        static int stage; static float t0; static Vector3 start, rabbitHome; static string log = "";
        static void Note(string s) { log += s + "\n"; Debug.Log("QINGXI_SMOKE " + s); }
        static void Tick()
        {
            if (!EditorApplication.isPlaying) return;
            var p = Object.FindFirstObjectByType<QingxiFirstPerson>(); if (p == null) return;
            var cc = p.GetComponent<CharacterController>(); var rabbit = Object.FindObjectsByType<QingxiRabbit>(FindObjectsSortMode.None).First(r => r.spawnName == "A01");
            float t = Time.time;
            switch (stage)
            {
                case 0: if (t < 1) return; p.Teleport(2); start = p.transform.position; t0 = t; stage = 1; Note("teleport hunt spawn " + start); return;
                case 1: cc.Move(p.transform.forward * 4 * Time.deltaTime + Vector3.down * 2 * Time.deltaTime); if (t - t0 < 2) return;
                    Note("walked 2 s: " + Vector3.Distance(start, p.transform.position).ToString("0.00") + " m, grounded " + cc.isGrounded); stage = 2; return;
                case 2: p.Teleport(5); rabbitHome = rabbit.transform.position; t0 = t; stage = 3; Note("teleport rabbit slope, A01 at " + rabbitHome); return;
                case 3: var toward = (rabbitHome - p.transform.position); toward.y = 0;
                    if (toward.magnitude > 5) { cc.Move(toward.normalized * 4 * Time.deltaTime + Vector3.down * 2 * Time.deltaTime); if (t - t0 < 12) return; }
                    Note("reached " + toward.magnitude.ToString("0.0") + " m from A01 home after " + (t - t0).ToString("0.0") + " s"); t0 = t; stage = 4; return;
                case 4: if (t - t0 < 5) return;
                    float moved = Vector3.Distance(new Vector3(rabbitHome.x, 0, rabbitHome.z), new Vector3(rabbit.transform.position.x, 0, rabbit.transform.position.z));
                    Note("A01 moved " + moved.ToString("0.0") + " m after the player came within notice radius (expect > 5)");
                    var c = p.transform.position; cc.enabled = false; p.transform.position = rabbit.transform.position + Vector3.right; cc.enabled = true;
                    Note("catch: " + rabbit.TryCatch(p.transform.position, 2.2f) + ", caught " + rabbit.IsCaught + ", respawn in " + rabbit.RespawnIn.ToString("0"));
                    bool pass = moved > 5 && rabbit.IsCaught && log.Contains("grounded True");
                    Note(pass ? "PASS" : "FAIL");
                    var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/qingxi-world")); Directory.CreateDirectory(dir);
                    File.WriteAllText(Path.Combine(dir, "play_smoke.txt"), log);
                    SessionState.SetBool(Key, false); EditorApplication.update -= Tick; stage = 5;
                    EditorApplication.ExitPlaymode(); EditorApplication.Exit(pass ? 0 : 1); return;
            }
        }
    }
}
