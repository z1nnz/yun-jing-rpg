using QingxiWorld;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace YunJing
{
    // F-key stations that connect the collaborator zones to the novice village: the door of
    // joshsu54's alchemy workshop (his AlchemyRoom scene, server-authoritative), Eli-0731's
    // return sorting table, and the ladder of Johnnnny0823's A10 watch platform.
    public sealed class QingxiAbcStations : MonoBehaviour
    {
        public const string AlchemyScene = "AlchemyRoom";
        public const string VillageScene = "QingxiNoviceVillage";
        const float Reach = 2.4f;

        public const string LodgingScene = "QingxiLodgingInterior";

        public Transform alchemyDoor, returnTable;
        public Transform lodgingDoor;              // village: front door of the lodging house
        public Transform exitDoor, bed, chest;     // lodging interior
        public QingxiForestEncounter forest;
        public QingxiFirstPerson walker;
        public QingxiTrainingPractice training;   // Johnnnny0823's training drills (posts, or the cushion indoors)
        public QingxiTerritoryFields fields;     // K23: the spirit fields in the newcomer's own territory
        public QingxiFortunes fortunes;           // 機緣 (K4): hidden finds, checked after every station

        // Set by QingxiSceneReturn when the player leaves the alchemy room, and by the lodging exit door.
        public static bool ReturningFromAlchemy, ReturningFromLodging;

        public bool SortingOpen { get; set; }
        public event System.Action SortingRequested;

        void Start()
        {
            if (walker == null) walker = QingxiFirstPerson.Current;
            if (walker == null) return;
            var foraging = GetComponent<QingxiLocalForaging>();
            if (ReturningFromAlchemy && alchemyDoor != null) { ReturningFromAlchemy = false; Place(alchemyDoor); foraging?.RestoreCarried(); }
            else if (ReturningFromLodging && lodgingDoor != null) { ReturningFromLodging = false; Place(lodgingDoor); foraging?.RestoreCarried("走出借住處，回到青溪村"); }
            else if (exitDoor != null) foraging?.RestoreCarried("進入借住處");
        }

        void Place(Transform door)
        {
            var body = walker.GetComponent<CharacterController>();
            body.enabled = false;
            walker.transform.position = door.position + Vector3.up * .05f;
            walker.transform.rotation = Quaternion.LookRotation(-door.forward);
            body.enabled = true;
        }

        static float Flat(Vector3 a, Vector3 b) => Vector2.Distance(new Vector2(a.x, a.z), new Vector2(b.x, b.z));

        public string Prompt(Vector3 position)
        {
            var practice = training != null ? training.Prompt(position) : null;
            if (practice != null) return practice;
            if (lodgingDoor != null && Flat(position, lodgingDoor.position) <= Reach) return "F 推門回到自己的領地";
            if (exitDoor != null && Flat(position, exitDoor.position) <= Reach) return "F 推門出去，回到青溪村";
            if (bed != null && Flat(position, bed.position) <= Reach) return "F 在床上歇息片刻";
            if (chest != null && Flat(position, chest.position) <= Reach) return "F 打開儲物箱";
            if (alchemyDoor != null && Flat(position, alchemyDoor.position) <= Reach) return "F 進入溪畔丹房（joshsu54 煉製玩法，需本機 API）";
            if (returnTable != null && Flat(position, returnTable.position) <= Reach) return "F 在分揀桌整理回村樣本（保存／留待煉製／交委託展示）";
            if (forest != null && forest.NearLadder(position)) return forest.Climbed ? "F 爬下觀察台" : "F 爬上觀察台（安全點）";
            var field = fields != null ? fields.Prompt(position) : null;
            if (field != null) return field;
            var clue = QingxiUpstreamClues.Current != null ? QingxiUpstreamClues.Current.Prompt(position) : null;
            if (clue != null) return clue;
            return fortunes != null ? fortunes.Prompt(position) : null;
        }

        public bool TryInteract(Vector3 position, out string message)
        {
            message = null;
            if (training != null && training.TryInteract(position, out message)) return true;
            var foraging = GetComponent<QingxiLocalForaging>();
            if (lodgingDoor != null && Flat(position, lodgingDoor.position) <= Reach)
            {
                if (!Application.CanStreamedLevelBeLoaded(LodgingScene)) { message = "借住處室內未包含在這個建置"; return true; }
                foraging?.Carry();
                QingxiSceneFade.ThroughDoor(LodgingScene, walker, lodgingDoor);
                message = "推門進屋";
                return true;
            }
            if (exitDoor != null && Flat(position, exitDoor.position) <= Reach)
            {
                foraging?.Carry();
                ReturningFromLodging = true;
                QingxiSceneFade.ThroughDoor(VillageScene, walker, exitDoor);
                message = "推門出去";
                return true;
            }
            if (bed != null && Flat(position, bed.position) <= Reach)
            {
                QingxiSceneFade.Blink();
                message = "歇息片刻，氣息平穩。（本機演練，不會跳過現實時間）";
                return true;
            }
            if (chest != null && Flat(position, chest.position) <= Reach)
            {
                message = "箱子是空的。正式背包接上服務端後，物品會放在這裡。";
                return true;
            }
            if (alchemyDoor != null && Flat(position, alchemyDoor.position) <= Reach)
            {
                if (!Application.CanStreamedLevelBeLoaded(AlchemyScene)) { message = "丹房場景未包含在這個建置"; return true; }
                GetComponent<QingxiLocalForaging>()?.Carry();
                QingxiSceneReturn.ReturnScene = SceneManager.GetActiveScene().name;
                SceneManager.LoadScene(AlchemyScene);
                message = "進入丹房";
                return true;
            }
            if (returnTable != null && Flat(position, returnTable.position) <= Reach)
            {
                SortingRequested?.Invoke();
                message = "攤開分揀桌：三份樣本可自由選去向";
                return true;
            }
            if (forest != null && forest.NearLadder(position)) { message = forest.ToggleClimb(); return true; }
            if (fields != null && fields.TryInteract(position, out message)) return true;
            if (QingxiUpstreamClues.Current != null && QingxiUpstreamClues.Current.TryInteract(position, out message)) return true;
            return fortunes != null && fortunes.TryInteract(position, out message);
        }
    }
}
