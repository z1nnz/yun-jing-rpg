using UnityEngine;

/// Paper lamp (TI04): E toggles the shade emission and a warm point light.
public class PaperLamp : Interactable
{
    public Material[] emissiveMats;
    public Light lampLight;
    public Color emitColor = new Color(1f, .72f, .42f);
    public bool on;
    float level, hold;

    public override bool HoldsCamera => hold > 0f;     // brief close-up after each toggle

    public override string Prompt => on ? "[E] 熄燈" : "[E] 點燈";

    public override void Interact(PlayerAvatar player)
    {
        on = !on; hold = 1.8f;
        if (InteriorUI.Instance) InteriorUI.Instance.Toast(on ? "點亮了燈" : "熄了燈");
    }

    public override void Tick(float dt)
    {
        hold -= dt;
        level = Mathf.MoveTowards(level, on ? 1f : 0f, dt / .3f);
        if (lampLight) { lampLight.enabled = level > .01f; lampLight.intensity = level * 2.4f; }
        SetEmission(emissiveMats, emitColor * (level * 1.6f));
    }

    public string Status => on ? "燈：亮" : "燈：熄";
}
