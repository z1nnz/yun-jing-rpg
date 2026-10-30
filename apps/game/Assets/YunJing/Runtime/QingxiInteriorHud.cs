using QingxiWorld;
using UnityEngine;

namespace YunJing
{
    // Small HUD for interior scenes: where you are, what F does here, and the last result.
    public sealed class QingxiInteriorHud : MonoBehaviour
    {
        public string place = "借住處";
        public QingxiAbcStations stations;
        public QingxiTrainingPractice training;

        void OnGUI()
        {
            QingxiFonts.ApplyImgui();
            var walker = QingxiFirstPerson.Current;
            if (walker == null || (training != null && training.Active)) return;
            float scale = Mathf.Clamp(Screen.height / 720f, .7f, 2f);
            var previous = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
            string prompt = stations != null ? stations.Prompt(walker.transform.position) : null;
            var today = QingxiNoviceDays.Objective;
            if (today != null) GUI.Box(new Rect(16, 96, 420, 30), $"新手第 {QingxiNoviceDays.Day} 天：{today}");
            GUI.Box(new Rect(16, 16, 420, 74), $"{place}\n{prompt ?? "WASD／搖桿 走動　F 互動"}\n{walker.LastLog}");
            GUI.matrix = previous;
        }
    }
}
