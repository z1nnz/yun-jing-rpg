using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace YunJing
{
    // K7: the novice village talks to the game server when one is reachable, and plays offline otherwise.
    // Logs in with a per-device local identity (dev auth, /v1/auth/local), allocates the birth once if needed,
    // and sends village results as server actions through GameApi (request IDs, retries, receipts). Actions
    // are queued and sent one at a time; anything done offline is replayed on the next connection (the server
    // grants each 機緣 once, so a replay never doubles a reward).
    public sealed class QingxiServerLink : MonoBehaviour
    {
        public static QingxiServerLink Current { get; private set; }
        public static bool Online => Current != null && Current.api != null && Current.api.Session != null && Current.api.State != null;
        public GameApi api;
        public string Status { get; private set; } = "離線";

        readonly Queue<GameAction> queue = new Queue<GameAction>();
        public bool Connecting { get; private set; } = true;   // still logging in: actions wait in the queue

        // One link for the whole session: entering the lodging or the alchemy room and coming back must not log in
        // again (the village scene would otherwise bring a second link).
        void Awake()
        {
            if (Current != null && Current != this) { Destroy(gameObject); return; }
            Current = this;
            DontDestroyOnLoad(gameObject);
        }

        IEnumerator Start()
        {
            if (Current != this) { Connecting = false; yield break; }
            if (api == null) api = GetComponent<GameApi>() ?? gameObject.AddComponent<GameApi>();
            string alias;
            try
            {
                alias = PlayerPrefs.GetString("yj.alias", "");
                if (alias.Length == 0) { alias = "qingxi-" + System.Guid.NewGuid().ToString("N").Substring(0, 10); PlayerPrefs.SetString("yj.alias", alias); PlayerPrefs.Save(); }
            }
            catch { alias = "qingxi-guest"; }
            api.Login(alias);
            float give = Time.realtimeSinceStartup + 6;
            while ((api.Busy || api.State == null) && Time.realtimeSinceStartup < give) yield return null;
            if (api.State == null) { Connecting = false; queue.Clear(); Status = "離線：本機紀錄"; Debug.Log("QINGXI_SERVER offline (" + api.Status + ")"); yield break; }
            if (api.State.birth == null && !api.State.birthAssigned)
            {
                bool done = false; api.Act(new GameAction { kind = "birth" }, (ok, _) => done = true);
                while (!done) yield return null;
            }
            Connecting = false;
            Status = "已連線：結果由伺服器保存";
            Debug.Log("QINGXI_SERVER online as " + alias);
            // Replay 機緣 found offline; the server ignores ones it already has.
            var fortunes = QingxiFortunes.Current;
            if (fortunes != null)
                foreach (var f in fortunes.fortunes)
                    if (QingxiFortunes.IsFoundLocally(f) && !HasFortune(f.id)) Submit(new GameAction { kind = "discover-fortune", fortune = f.id });
        }

        public bool HasFortune(string id) => Online && api.State.player.fortunes != null && System.Array.IndexOf(api.State.player.fortunes, id) >= 0;

        public void Submit(GameAction action) { if (Online || Connecting) queue.Enqueue(action); }

        public int Quantity(string item)
        {
            int n = 0;
            if (Online && api.State.player.inventory != null) foreach (var stack in api.State.player.inventory) if (stack.item == item) n += stack.quantity;
            return n;
        }

        void Update()
        {
            if (!Online || queue.Count == 0 || api.Busy || api.HasPending) return;
            var action = queue.Dequeue();
            api.Act(action, (ok, error) =>
            {
                if (ok) return;
                Debug.LogWarning($"QINGXI_SERVER {action.kind} refused: {error}");
                if (action.kind == "waterworks-commit") QingxiWaterworksSite.Refused();
                // Tell the player why (for example no spirit root yet, or still regrowing), in the server's words.
                var message = (error ?? "").Split('·')[0].Trim();
                if (message.Length > 0) FindAnyObjectByType<QingxiLocalForaging>()?.Notice("伺服器：" + message);
            });
        }
    }
}
