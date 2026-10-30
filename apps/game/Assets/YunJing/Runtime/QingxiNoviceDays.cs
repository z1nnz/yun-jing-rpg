using System;
using System.Collections.Generic;
using UnityEngine;

namespace YunJing
{
    // The novice chapter's ten days (docs/story/outline-v1.md, section 三): which day it is and what the newcomer has
    // done today, so the HUD can say what today is about. Nothing here is required; it is a thread to follow.
    // Day 1: arrive on the road, drink tea with the old man at the roadside pavilion (he gives a plum seedling),
    // be given an empty house (the lodging door), plant the seedling in the yard, sleep. Day 2 begins in the morning.
    // Kept on this device (PlayerPrefs) until the server keeps the days.
    public static class QingxiNoviceDays
    {
        const string DayKey = "yj.noviceDay", DoneKey = "yj.noviceDone";

        public static event Action Changed;

        public static int Day
        {
            get { try { return Mathf.Max(1, PlayerPrefs.GetInt(DayKey, 1)); } catch { return 1; } }
        }

        static HashSet<string> Done()
        {
            try { return new HashSet<string>(PlayerPrefs.GetString(DoneKey, "").Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)); }
            catch { return new HashSet<string>(); }
        }

        public static bool Has(string step) => Done().Contains(step);

        public static void Mark(string step)
        {
            var done = Done();
            if (!done.Add(step)) return;
            try { PlayerPrefs.SetString(DoneKey, string.Join(",", done)); PlayerPrefs.Save(); } catch { }
            Changed?.Invoke();
        }

        /// <summary>What today is about, in one line (null when the chapter's thread has nothing to say).</summary>
        public static string Objective
        {
            get
            {
                if (Day == 1)
                {
                    if (!Has("tea")) return "沿官道往村子走，路邊有座茶亭";
                    if (!Has("house")) return "進青溪村，到借住處推門，看看分給你的空屋";
                    if (!Has("plum")) return "把茶亭老人給的梅苗種在院子裡";
                    return "天黑了，回屋裡的床上歇息";
                }
                if (Day == 2) return "第二天：在院子種下第一塊田；到村裡的練功場找沈岳";
                return null;
            }
        }

        /// <summary>Sleeping in the bed: the first night ends day 1 once the seedling is in the ground.</summary>
        public static string Rest()
        {
            if (Day != 1 || !Has("plum")) return null;
            try { PlayerPrefs.SetInt(DayKey, 2); PlayerPrefs.Save(); } catch { }
            Changed?.Invoke();
            return "一夜過去。天亮時，屋前那株梅苗還立在那裡。";
        }

        /// <summary>Starts the chapter over on this device (the smoke test and review captures use it).</summary>
        public static void Reset()
        {
            try { PlayerPrefs.DeleteKey(DayKey); PlayerPrefs.DeleteKey(DoneKey); PlayerPrefs.Save(); } catch { }
            Changed?.Invoke();
        }
    }
}
