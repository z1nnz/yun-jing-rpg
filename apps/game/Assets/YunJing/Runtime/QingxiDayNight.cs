using System;
using System.Collections;
using System.Text.RegularExpressions;
using UnityEngine;

namespace YunJing
{
    // K11: the time of day follows the player's real clock. Sun (moonlight at night), ambient light, fog and the
    // procedural sky move smoothly through dawn, morning, noon, afternoon, dusk and night; night lights (lanterns,
    // doorways) fade in after dusk. For testing: --time=21.5 or ?time=21.5 fixes the hour, --day-speed=600 runs
    // the clock 600× faster, --time-shots saves a screenshot at four hours next to the player and quits.
    public sealed class QingxiDayNight : MonoBehaviour
    {
        public Light sun;
        public Material sky;            // Skybox/Procedural
        public Light[] nightLights = new Light[0];
        public Renderer[] nightGlows = new Renderer[0];   // emissive cards beside the night lights
        public float fogScale = 1;      // interiors and small scenes can keep a shorter fog

        public static QingxiDayNight Current { get; private set; }
        public float Hour { get; private set; }
        /// <summary>0 by day, 1 at full night; ramps over dusk (18–19.5) and dawn (5–6.5).</summary>
        public float Night { get; private set; }
        public static bool IsNight => Current != null && Current.Night > .5f;

        float? fixedHour; float speed = 1; double startedAt; DateTime startClock;
        float[] lightBase;

        struct Key
        {
            public float hour, pitch, yaw, intensity, exposure, fogEnd;
            public Color light, sky, equator, ground, fog, tint;
        }

        // Keyframes through the day. Yaw follows the sun east (−90) → south (0) → west (+90); at night the light
        // is the moon, high in the south-east.
        static readonly Key[] Keys =
        {
            K(0, 40, 140, .32f, new Color(.6f, .7f, .95f), new Color(.2f, .25f, .38f), new Color(.15f, .17f, .24f), new Color(.07f, .07f, .09f), new Color(.13f, .16f, .24f), .22f, new Color(.2f, .27f, .5f), 90),
            K(4.8f, 38, 150, .3f,  new Color(.6f, .7f, .95f), new Color(.21f, .25f, .38f), new Color(.16f, .17f, .24f), new Color(.07f, .07f, .09f), new Color(.15f, .17f, .25f), .25f, new Color(.22f, .28f, .5f), 90),
            K(5.8f, 5, -100, .5f,  new Color(1f, .62f, .44f),  new Color(.46f, .44f, .54f), new Color(.52f, .42f, .40f), new Color(.2f, .17f, .16f),  new Color(.78f, .66f, .64f), .7f, new Color(.62f, .52f, .58f), 100),
            K(8,    34, -35, 1.35f, new Color(1f, .9f, .74f), new Color(.62f, .7f, .78f),  new Color(.55f, .58f, .52f), new Color(.32f, .3f, .26f),  new Color(.78f, .83f, .84f), 1.2f, new Color(.5f, .62f, .74f), 120),
            K(12.5f, 58, 5, 1.35f, new Color(1f, .94f, .84f),  new Color(.66f, .74f, .82f), new Color(.6f, .63f, .58f),  new Color(.34f, .32f, .28f), new Color(.8f, .85f, .88f),  1.3f, new Color(.48f, .62f, .78f), 135),
            K(16,   34, 60, 1.1f,  new Color(1f, .9f, .76f),   new Color(.62f, .66f, .72f), new Color(.58f, .56f, .5f),  new Color(.32f, .28f, .24f), new Color(.8f, .8f, .78f),   1.15f, new Color(.55f, .6f, .7f), 125),
            K(18,   6, 95, .6f,    new Color(1f, .55f, .32f),  new Color(.5f, .42f, .5f),   new Color(.56f, .4f, .34f),  new Color(.22f, .16f, .14f), new Color(.76f, .56f, .48f), .75f, new Color(.72f, .46f, .42f), 105),
            K(19.5f, 30, 130, .18f, new Color(.5f, .55f, .85f), new Color(.2f, .2f, .32f),   new Color(.16f, .14f, .2f),  new Color(.07f, .06f, .08f), new Color(.2f, .19f, .28f),  .28f, new Color(.28f, .26f, .5f), 90),
            K(21, 38, 140, .32f, new Color(.6f, .7f, .95f), new Color(.2f, .25f, .38f), new Color(.15f, .17f, .24f), new Color(.07f, .07f, .09f), new Color(.13f, .16f, .24f), .22f, new Color(.2f, .27f, .5f), 90),
        };

        static Key K(float h, float pitch, float yaw, float intensity, Color light, Color sky, Color equator, Color ground, Color fog, float exposure, Color tint, float fogEnd)
            => new Key { hour = h, pitch = pitch, yaw = yaw, intensity = intensity, light = light, sky = sky, equator = equator, ground = ground, fog = fog, exposure = exposure, tint = tint, fogEnd = fogEnd };

        public static string PhaseName(float hour) =>
            hour < 5 ? "深夜" : hour < 7 ? "清晨" : hour < 11 ? "上午" : hour < 14 ? "正午" : hour < 17 ? "午後" : hour < 19.5f ? "黃昏" : "入夜";

        void Awake()
        {
            Current = this;
            if (sky != null) { sky = new Material(sky); RenderSettings.skybox = sky; }
            string args = string.Join(" ", Environment.GetCommandLineArgs()) + " " + Application.absoluteURL;
            var t = Regex.Match(args, @"time=(\d+(\.\d+)?)");
            if (t.Success) fixedHour = Mathf.Repeat(float.Parse(t.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture), 24);
            else if (args.Contains("abc-smoke")) fixedHour = 10;   // automated checks see the same morning every run
            var s = Regex.Match(args, @"day-speed=(\d+(\.\d+)?)");
            if (s.Success) speed = float.Parse(s.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
            startedAt = Time.realtimeSinceStartupAsDouble; startClock = DateTime.Now;
            lightBase = new float[nightLights.Length];
            for (int i = 0; i < nightLights.Length; i++) lightBase[i] = nightLights[i] != null ? nightLights[i].intensity : 0;
            Apply(CurrentHour());
        }

        /// <summary>Fixes the hour (tests and screenshots); null returns to the real clock.</summary>
        public void SetHour(float? hour) { fixedHour = hour.HasValue ? Mathf.Repeat(hour.Value, 24) : (float?)null; Apply(CurrentHour()); }

        float CurrentHour()
        {
            if (fixedHour.HasValue && speed <= 1) return fixedHour.Value;
            var clock = startClock.AddSeconds((Time.realtimeSinceStartupAsDouble - startedAt) * speed);
            float h = clock.Hour + clock.Minute / 60f + clock.Second / 3600f;
            return fixedHour.HasValue ? Mathf.Repeat(fixedHour.Value + (float)((Time.realtimeSinceStartupAsDouble - startedAt) * speed / 3600), 24) : h;
        }

        IEnumerator Start()
        {
            string args = string.Join(" ", Environment.GetCommandLineArgs());
            if (!args.Contains("--time-shots")) yield break;
            string dir = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Application.dataPath), "time-shots");
            System.IO.Directory.CreateDirectory(dir);
            yield return new WaitForSecondsRealtime(4);
            IEnumerator Shot(string name)
            {
                yield return new WaitForSecondsRealtime(1.2f);
                yield return new WaitForEndOfFrame();
                var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); tex.Apply();
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(dir, name + ".png"), tex.EncodeToPNG());
                Destroy(tex);
            }
            foreach (var hour in new[] { 6f, 10f, 12.5f, 16f, 18.2f, 22f })
            {
                SetHour(hour);
                yield return Shot($"{hour:00.0}-{PhaseName(hour)}");
            }
            // The night once more from the market road, looking up at the plaza and the lodging's lanterns.
            var walker = QingxiWorld.QingxiFirstPerson.Current;
            var body = walker != null ? walker.GetComponent<CharacterController>() : null;
            if (body != null)
            {
                body.enabled = false;
                walker.transform.SetPositionAndRotation(new Vector3(0, walker.transform.position.y + .5f, -14), Quaternion.identity);
                body.enabled = true;
                SetHour(22);
                yield return Shot("22.0-入夜-坊市");
            }
            Debug.Log("QINGXI_TIME_SHOTS saved to " + dir);
            Application.Quit();
        }

        void Update()
        {
            float h = CurrentHour();
            if (Mathf.Abs(Mathf.DeltaAngle(h * 15, Hour * 15)) > .01f) Apply(h);
        }

        void Apply(float hour)
        {
            Hour = hour;
            int i = 0;
            while (i < Keys.Length - 1 && Keys[i + 1].hour <= hour) i++;
            var a = Keys[i]; var b = i + 1 < Keys.Length ? Keys[i + 1] : Keys[0];
            float span = (b.hour > a.hour ? b.hour : b.hour + 24) - a.hour;
            float t = Mathf.SmoothStep(0, 1, span > 0 ? (hour - a.hour) / span : 0);

            if (sun != null)
            {
                sun.transform.rotation = Quaternion.Slerp(Quaternion.Euler(a.pitch, a.yaw, 0), Quaternion.Euler(b.pitch, b.yaw, 0), t);
                sun.color = Color.Lerp(a.light, b.light, t);
                sun.intensity = Mathf.Lerp(a.intensity, b.intensity, t);
            }
            RenderSettings.ambientSkyColor = Color.Lerp(a.sky, b.sky, t);
            RenderSettings.ambientEquatorColor = Color.Lerp(a.equator, b.equator, t);
            RenderSettings.ambientGroundColor = Color.Lerp(a.ground, b.ground, t);
            RenderSettings.fogColor = Color.Lerp(a.fog, b.fog, t);
            RenderSettings.fogEndDistance = Mathf.Lerp(a.fogEnd, b.fogEnd, t) * fogScale;
            RenderSettings.fogStartDistance = RenderSettings.fogEndDistance * .38f;
            if (sky != null)
            {
                sky.SetFloat("_Exposure", Mathf.Lerp(a.exposure, b.exposure, t));
                sky.SetColor("_SkyTint", Color.Lerp(a.tint, b.tint, t));
                sky.SetColor("_GroundColor", Color.Lerp(a.fog, b.fog, t));
            }

            Night = hour >= 19.5f || hour < 5f ? 1 : hour >= 18 ? Mathf.InverseLerp(18, 19.5f, hour) : hour < 6.5f ? Mathf.InverseLerp(6.5f, 5, hour) : 0;
            for (int n = 0; n < nightLights.Length; n++)
                if (nightLights[n] != null)
                {
                    nightLights[n].intensity = lightBase[n] * Night;
                    nightLights[n].enabled = Night > .01f;
                }
            foreach (var g in nightGlows) if (g != null) g.enabled = Night > .05f;
        }
    }
}
