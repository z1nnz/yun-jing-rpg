// Kit models and their ports in Unity space.
//
// The FBX exports carry SOCKET_<port> empties; model_info.json carries the same ports in Blender coordinates with their
// normals. The Blender -> Unity axis map is solved once from the sockets (best signed axis permutation), so ports and
// pivots are never hand-converted, and a change in the exporter's axis settings shows up as a solve error, not a
// silently mirrored kit.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using static Qingxi.Waterworks.MiniJson;

namespace Qingxi.Waterworks
{
    public sealed class KitPort { public string Name; public Vector3 Pos, Normal; }

    public sealed class KitModel
    {
        public string Key; public GameObject Prefab;
        public readonly Dictionary<string, KitPort> Ports = new Dictionary<string, KitPort>();
        public readonly Dictionary<string, KitPort> Sockets = new Dictionary<string, KitPort>();
        public Vector3 Centre;                                                   // mean of the port positions (for loose placement)
    }

    public static class Kit
    {
        static readonly Dictionary<string, KitModel> cache = new Dictionary<string, KitModel>();
        static Matrix4x4? axes;                                                    // Blender (Z up) -> Unity (Y up) in prefab space
        public static float AxisSolveError { get; private set; }

        public static Matrix4x4 Axes => axes ??= SolveAxes("B04_TeeTrough");
        public static Vector3 FromBlender(IList<object> v) => Axes.MultiplyVector(new Vector3((float)D(v[0]), (float)D(v[1]), (float)D(v[2])));

        static Dictionary<string, object> Info(string key) => O(Parse(Resources.Load<TextAsset>($"Kit/{key}/{key}_model_info").text));
        static GameObject Prefab(string key) => Resources.Load<GameObject>($"Kit/{key}/{key}") ?? throw new MissingReferenceException($"Kit/{key} not synced (Waterworks > Sync Kit)");

        static Dictionary<string, Vector3> SocketPositions(GameObject prefab)
        {
            // the prefab root keeps its own pose when instantiated under a holder, so express sockets in the root's parent space
            var root = prefab.transform; var m = Matrix4x4.TRS(root.localPosition, root.localRotation, root.localScale);
            var d = new Dictionary<string, Vector3>();
            foreach (var t in prefab.GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("SOCKET_")) d[t.name.Substring(7).Split('.')[0]] = m.MultiplyPoint3x4(root.InverseTransformPoint(t.position));
            return d;
        }

        /// <summary>Signed axis permutation that maps the model_info port positions onto the FBX sockets.</summary>
        static Matrix4x4 SolveAxes(string key)
        {
            var info = Info(key); var sockets = SocketPositions(Prefab(key));
            var pairs = L(info["ports"]).Select(O).Where(p => sockets.ContainsKey(S(p["name"])))
                .Select(p => (b: new Vector3((float)D(L(p["position"])[0]), (float)D(L(p["position"])[1]), (float)D(L(p["position"])[2])), u: sockets[S(p["name"])])).ToList();
            if (pairs.Count < 2) throw new MissingReferenceException($"{key}: need two sockets to solve the axis map, found {pairs.Count}");
            var best = Matrix4x4.identity; float err = float.MaxValue;
            int[][] perms = { new[] { 0, 1, 2 }, new[] { 0, 2, 1 }, new[] { 1, 0, 2 }, new[] { 1, 2, 0 }, new[] { 2, 0, 1 }, new[] { 2, 1, 0 } };
            foreach (var p in perms)
                for (int sg = 0; sg < 8; sg++)
                {
                    var m = Matrix4x4.zero; m.m33 = 1;
                    for (int r = 0; r < 3; r++) m[r, p[r]] = ((sg >> r) & 1) == 0 ? 1 : -1;
                    float e = pairs.Sum(x => (m.MultiplyVector(x.b) - x.u).sqrMagnitude);
                    if (e < err) { err = e; best = m; }
                }
            AxisSolveError = Mathf.Sqrt(err / pairs.Count);
            if (AxisSolveError > 0.01f) Debug.LogWarning($"[Waterworks] axis solve residual {AxisSolveError:0.000} m on {key}: FBX sockets do not match model_info");
            if ((best.MultiplyVector(Vector3.forward) - Vector3.up).sqrMagnitude > 1e-4f) Debug.LogWarning("[Waterworks] Blender up does not map to Unity up");
            return best;
        }

        public static KitModel Get(string key)
        {
            if (cache.TryGetValue(key, out var k)) return k;
            var info = Info(key); k = new KitModel { Key = key, Prefab = Prefab(key) };
            foreach (var p in L(info["ports"]).Select(O))
                k.Ports[S(p["name"])] = new KitPort { Name = S(p["name"]), Pos = FromBlender(L(p["position"])), Normal = FromBlender(L(p["normal"])).normalized };
            foreach (var p in L(info["sockets"]).Select(O))
                k.Sockets[S(p["name"])] = new KitPort { Name = S(p["name"]), Pos = FromBlender(L(p["position"])), Normal = FromBlender(L(p["normal"])).normalized };
            k.Centre = k.Ports.Count > 1 ? k.Ports.Values.Aggregate(Vector3.zero, (a, p) => a + p.Pos) / k.Ports.Count : Vector3.zero;
            k.Centre.y = 0;
            return cache[key] = k;
        }

        /// <summary>Pose (position, yaw in degrees about +Y) that sets port `inPort` of `model` face to face on a world port.</summary>
        public static (Vector3 pos, float yaw) Snap(Vector3 worldPortPos, Vector3 worldPortNormal, KitModel model, string inPort)
        {
            var p = model.Ports[inPort]; var want = -worldPortNormal; want.y = 0; var have = p.Normal; have.y = 0;
            float yaw = Vector3.SignedAngle(have, want, Vector3.up);
            return (worldPortPos - Quaternion.Euler(0, yaw, 0) * p.Pos, yaw);
        }

        public static Vector3 World(Vector3 pos, float yaw, Vector3 local) => pos + Quaternion.Euler(0, yaw, 0) * local;
        public static Vector3 Dir(float yaw, Vector3 local) => Quaternion.Euler(0, yaw, 0) * local;
    }
}
