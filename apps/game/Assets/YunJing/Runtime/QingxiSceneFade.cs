using System.Collections;
using QingxiWorld;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace YunJing
{
    // Door transition between the village and an interior scene: the player steps toward the door while the
    // screen fades to black, the next scene loads, then the screen fades back in. Also a short blink for resting.
    public sealed class QingxiSceneFade : MonoBehaviour
    {
        static QingxiSceneFade runner;
        public static bool Busy { get; private set; }
        float alpha;

        static QingxiSceneFade Runner()
        {
            if (runner == null)
            {
                runner = new GameObject("Qingxi scene fade").AddComponent<QingxiSceneFade>();
                DontDestroyOnLoad(runner.gameObject);
            }
            return runner;
        }

        public static void ThroughDoor(string scene, QingxiFirstPerson walker, Transform door)
        {
            if (Busy) return;
            Runner().StartCoroutine(runner.Door(scene, walker, door));
        }

        public static void Blink() { if (!Busy) Runner().StartCoroutine(runner.BlinkRoutine()); }

        /// <summary>A door inside one scene (the territory's house and room): fade out, stand the player at the
        /// other door looking the way it faces, fade back in.</summary>
        public static void Within(QingxiFirstPerson walker, Transform to)
        {
            if (Busy || walker == null || to == null) return;
            Runner().StartCoroutine(runner.WithinRoutine(walker, to));
        }

        IEnumerator WithinRoutine(QingxiFirstPerson walker, Transform to)
        {
            Busy = true;
            walker.SetMenuOpen(true);
            for (float t = 0; t < .4f; t += Time.unscaledDeltaTime) { alpha = t / .4f; yield return null; }
            alpha = 1;
            var body = walker.GetComponent<CharacterController>();
            if (body != null) body.enabled = false;
            walker.transform.position = to.position + Vector3.up * .05f;
            walker.transform.rotation = Quaternion.LookRotation(to.forward);
            if (body != null) body.enabled = true;
            yield return null;
            walker.SetMenuOpen(false);
            for (float t = 0; t < .4f; t += Time.unscaledDeltaTime) { alpha = 1 - t / .4f; yield return null; }
            alpha = 0;
            Busy = false;
        }

        IEnumerator Door(string scene, QingxiFirstPerson walker, Transform door)
        {
            Busy = true;
            if (walker != null) walker.SetMenuOpen(true);   // stop walking while the door "opens"
            Vector3 from = walker != null ? walker.transform.position : Vector3.zero;
            Vector3 toward = door != null && walker != null ? door.position - from : Vector3.zero;
            toward.y = 0;
            Vector3 to = from + (toward.sqrMagnitude > .01f ? toward.normalized * .7f : Vector3.zero);
            for (float t = 0; t < .5f; t += Time.unscaledDeltaTime)
            {
                alpha = t / .5f;
                if (walker != null) walker.transform.position = Vector3.Lerp(from, to, alpha);
                yield return null;
            }
            alpha = 1;
            SceneManager.LoadScene(scene);
            yield return null; yield return null;
            for (float t = 0; t < .45f; t += Time.unscaledDeltaTime) { alpha = 1 - t / .45f; yield return null; }
            alpha = 0;
            Busy = false;
        }

        IEnumerator BlinkRoutine()
        {
            Busy = true;
            for (float t = 0; t < .6f; t += Time.unscaledDeltaTime) { alpha = t / .6f; yield return null; }
            yield return new WaitForSecondsRealtime(.4f);
            for (float t = 0; t < .6f; t += Time.unscaledDeltaTime) { alpha = 1 - t / .6f; yield return null; }
            alpha = 0;
            Busy = false;
        }

        void OnGUI()
        {
            if (alpha <= 0) return;
            GUI.depth = -1000;
            var old = GUI.color;
            GUI.color = new Color(0, 0, 0, Mathf.Clamp01(alpha));
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), Texture2D.whiteTexture);
            GUI.color = old;
        }
    }
}
