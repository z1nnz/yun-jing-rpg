using UnityEngine;

/// Base for anything the player can use with E. Tick() is driven by Update in play mode,
/// or by DemoDirector when it is stepping time itself (recording).
public abstract class Interactable : MonoBehaviour
{
    public Transform standPoint;            // where the player stands, facing the item
    public abstract string Prompt { get; }
    public abstract void Interact(PlayerAvatar player);
    public virtual void Tick(float dt) { }

    /// While true the camera leaves the shoulder follow and frames this item (panel open, lying in bed).
    public virtual bool HoldsCamera => false;
    public Vector3 shotFocus;               // world point the close-up looks at
    public float shotDistance = 3f, shotYaw, shotPitch = 40f, shotFov = 36f;

    void Update()
    {
        if (!DemoDirector.Driving) Tick(Time.deltaTime);
    }

    protected static void SetEmission(Material[] mats, Color c)
    {
        foreach (var m in mats)
        {
            if (m == null) continue;
            m.SetColor("_EmissionColor", c);
        }
    }
}
