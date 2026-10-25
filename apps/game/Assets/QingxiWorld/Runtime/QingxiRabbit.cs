using UnityEngine;
using UnityEngine.AI;

namespace QingxiWorld
{
    // Play-mode stand-in for one mountain rabbit: idles at its spawn, flees along the rabbit NavMesh to the flee point
    // farthest from the player when the player comes within the notice radius (hunting.json: 7 m), waits, hops home, and
    // after being caught respawns at the same spawn after 90 s. Visual rehearsal only: no server hunt, health or drops.
    public sealed class QingxiRabbit : MonoBehaviour
    {
        public string spawnName;
        public Vector3[] fleePoints;
        public float noticeRadius = 7, fleeSpeed = 5, homeSpeed = 2.5f, respawnSeconds = 90, waitAtFlee = 8;

        enum State { Idle, Fleeing, Waiting, Returning, Caught }
        State state; Vector3 home; Vector3[] corners; int corner; float timer, hopPhase; Renderer[] renderers;
        public bool IsCaught => state == State.Caught;
        public float RespawnIn => state == State.Caught ? timer : 0;

        void Start() { home = transform.position; renderers = GetComponentsInChildren<Renderer>(); hopPhase = Random.value * 3; }

        public bool TryCatch(Vector3 player, float reach)
        {
            if (state == State.Caught || Vector3.Distance(Flat(player), Flat(transform.position)) > reach) return false;
            state = State.Caught; timer = respawnSeconds; foreach (var r in renderers) r.enabled = false; return true;
        }

        void Update()
        {
            var player = QingxiFirstPerson.Current; float dt = Time.deltaTime;
            switch (state)
            {
                case State.Caught:
                    timer -= dt;
                    if (timer <= 0) { transform.position = home; foreach (var r in renderers) r.enabled = true; state = State.Idle; }
                    return;
                case State.Idle:
                    Hop(.12f, 1.6f);
                    if (player != null && Vector3.Distance(Flat(player.transform.position), Flat(transform.position)) < noticeRadius) Flee(player.transform.position);
                    break;
                case State.Waiting:
                    Hop(.12f, 1.6f); timer -= dt;
                    if (player != null && Vector3.Distance(Flat(player.transform.position), Flat(transform.position)) < noticeRadius) Flee(player.transform.position);
                    else if (timer <= 0 && Route(home)) state = State.Returning;
                    break;
                case State.Fleeing:
                    if (Follow(fleeSpeed, .28f, .18f)) { state = State.Waiting; timer = waitAtFlee; }
                    break;
                case State.Returning:
                    if (player != null && Vector3.Distance(Flat(player.transform.position), Flat(transform.position)) < noticeRadius) { Flee(player.transform.position); break; }
                    if (Follow(homeSpeed, .15f, .35f)) state = State.Idle;
                    break;
            }
        }
        void Flee(Vector3 from)
        {
            Vector3 best = home; float bestD = -1;
            foreach (var p in fleePoints) { float d = Vector3.Distance(Flat(p), Flat(from)); if (d > bestD && Vector3.Distance(Flat(p), Flat(transform.position)) > 1.5f) { bestD = d; best = p; } }
            if (Route(best)) state = State.Fleeing;
        }
        bool Route(Vector3 to)
        {
            var path = new NavMeshPath();
            if (!NavMesh.SamplePosition(transform.position, out var a, 2, NavMesh.AllAreas) || !NavMesh.SamplePosition(to, out var b, 2, NavMesh.AllAreas)) return false;
            if (!NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, path) || path.corners.Length < 2) return false;
            corners = path.corners; corner = 1; return true;
        }
        bool Follow(float speed, float hopHeight, float hopTime)
        {
            if (corners == null || corner >= corners.Length) return true;
            var pos = transform.position; pos.y = corners[corner].y;
            var step = Vector3.MoveTowards(Flat(pos), Flat(corners[corner]), speed * Time.deltaTime);
            var dir = step - Flat(pos);
            float baseY = Mathf.Lerp(corners[Mathf.Max(0, corner - 1)].y, corners[corner].y, .5f);
            hopPhase += Time.deltaTime / hopTime;
            transform.position = new Vector3(step.x, baseY + Mathf.Abs(Mathf.Sin(hopPhase * Mathf.PI)) * hopHeight, step.z);
            if (dir.sqrMagnitude > 1e-6f) transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), 12 * Time.deltaTime);
            if (Vector3.Distance(Flat(transform.position), Flat(corners[corner])) < .05f) corner++;
            if (corner >= corners.Length) { var p = transform.position; p.y = corners[corners.Length - 1].y; transform.position = p; return true; }
            return false;
        }
        void Hop(float height, float period)
        {
            hopPhase += Time.deltaTime / period; float t = hopPhase % 1f;
            var p = transform.position; float ground = state == State.Idle ? home.y : (corners != null && corners.Length > 0 ? corners[corners.Length - 1].y : home.y);
            p.y = ground + (t < .22f ? Mathf.Sin(t / .22f * Mathf.PI) * height : 0); transform.position = p;
        }
        static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);
    }
}
