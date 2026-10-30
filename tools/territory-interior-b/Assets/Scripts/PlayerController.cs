using UnityEngine;

/// Play-mode control: WASD walks relative to the camera (mouse looks, Alt frees the cursor), E uses the nearest item,
/// Esc / E closes the chest panel, Esc leaves the furnace (hold F to fast-forward the fire), → / ← turn the journal's pages.
/// Disabled while DemoDirector is driving.
public class PlayerController : MonoBehaviour
{
    public PlayerAvatar avatar;
    public CameraRig rig;
    public Interactable[] interactables;
    public float reach = 1.0f;
    public Vector2 boundsMin = new Vector2(-3.25f, -2.25f), boundsMax = new Vector2(3.25f, 2.25f);

    void Update()
    {
        if (DemoDirector.Driving || avatar == null) return;
        var ui = InteriorUI.Instance;
        var touch = TouchControls.Instance;
        bool tap = touch && touch.ConsumeInteract();
        if (ui) ui.SetStatus(StatusLine(interactables));
        var chest = FindOpenChest();
        if (chest != null)
        {
            if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.E)) chest.Close();
            if (ui) ui.SetPrompt("");
            return;
        }
        foreach (var it in interactables)
            if (it is ShelfDisplay sh && sh.isOpen)
            {
                if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.E)) sh.Close();
                if (ui) ui.SetPrompt("");
                return;
            }
        foreach (var it in interactables)
            if (it is JournalDesk jd && jd.isOpen)
            {
                if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.E)) jd.Close();
                if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D)) jd.Next();
                if (Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A)) jd.Prev();
                if (ui) ui.SetPrompt("");
                return;
            }
        var furnace = FindOpenFurnace();
        if (furnace != null)
        {
            furnace.speed = Input.GetKey(KeyCode.F) ? 3f : 1f;
            if (Input.GetKeyDown(KeyCode.Escape)) furnace.Leave();
            if (ui) ui.SetPrompt("");
            return;
        }
        if (avatar.IsLying)
        {
            if (ui) ui.SetPrompt("[E] 起身");
            if ((Input.GetKeyDown(KeyCode.E) || tap) && !avatar.Busy) avatar.GetUp();
            return;
        }
        // camera-relative: W walks away from the camera
        Vector3 fwd = rig ? rig.Forward : Vector3.forward, right = new Vector3(fwd.z, 0f, -fwd.x);
        Vector2 stick = touch ? touch.Move : Vector2.zero;
        Vector3 dir = fwd * (Input.GetAxisRaw("Vertical") + stick.y) + right * (Input.GetAxisRaw("Horizontal") + stick.x);
        avatar.Move(dir, Time.deltaTime);
        var p = avatar.transform.position;
        avatar.transform.position = new Vector3(Mathf.Clamp(p.x, boundsMin.x, boundsMax.x), p.y, Mathf.Clamp(p.z, boundsMin.y, boundsMax.y));

        var near = Nearest();
        if (ui) ui.SetPrompt(near ? near.Prompt : "");
        if (near && (Input.GetKeyDown(KeyCode.E) || tap) && !avatar.Busy) near.Interact(avatar);
    }

    public Interactable Nearest()
    {
        Interactable best = null; float bd = reach;
        foreach (var it in interactables)
        {
            if (!it || !it.standPoint) continue;
            float d = Vector3.Distance(Flat(it.standPoint.position), Flat(avatar.transform.position));
            if (d < bd) { bd = d; best = it; }
        }
        return best;
    }

    FurnaceFire FindOpenFurnace()
    {
        foreach (var it in interactables) if (it is FurnaceFire f && f.panelOpen) return f;
        return null;
    }

    ChestStorage FindOpenChest()
    {
        foreach (var it in interactables) if (it is ChestStorage c && c.isOpen) return c;
        return null;
    }

    public static string StatusLine(Interactable[] items)
    {
        string a = "", b = "";
        foreach (var it in items)
        {
            if (it is FurnaceFire f) a = f.Status;
            if (it is PaperLamp l) b = l.Status;
        }
        return a + "　" + b;
    }

    static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0f, v.z);
}
