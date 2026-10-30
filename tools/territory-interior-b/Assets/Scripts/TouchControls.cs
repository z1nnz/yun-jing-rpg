using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// Landscape touch controls: a floating move stick on the left half, camera drag on the right half and an
/// interact button (bottom right) that stands in for E. Touches that start on a UI button are left to the UI.
/// The overlay only appears once a touch has been seen, so keyboard / mouse play is unchanged.
public class TouchControls : MonoBehaviour
{
    public static TouchControls Instance;
    public float stickRadius = 70f;                  // canvas units

    public Vector2 Move { get; private set; }        // x = right, y = forward, length ≤ 1
    public Vector2 Look { get; private set; }        // degrees this frame
    public bool Active { get; private set; }
    bool interact;

    int moveId = -1, lookId = -1;
    Vector2 moveOrigin, lookLast;
    RectTransform ring, knob, button;
    Text buttonLabel;

    void OnEnable() { Instance = this; }

    /// True once per tap of the interact button.
    public bool ConsumeInteract() { bool b = interact; interact = false; return b; }

    public void Build(RectTransform ringRt, RectTransform knobRt, RectTransform buttonRt)
    {
        ring = ringRt; knob = knobRt; button = buttonRt;
        buttonLabel = button.GetComponentInChildren<Text>();
        button.GetComponent<Button>().onClick.AddListener(() => interact = true);
        Show(false);
    }

    void Show(bool on)
    {
        if (button) button.gameObject.SetActive(on);
        if (ring) ring.gameObject.SetActive(on && moveId >= 0);
    }

    float Scale => ((RectTransform)transform).rect.width > 0 ? ((RectTransform)transform).rect.width / Screen.width : 1f;

    void Update()
    {
        Look = Vector2.zero;
        if (DemoDirector.Driving) return;
        for (int i = 0; i < Input.touchCount; i++)
        {
            var t = Input.GetTouch(i);
            Active = true;
            if (t.phase == TouchPhase.Began)
            {
                if (EventSystem.current && EventSystem.current.IsPointerOverGameObject(t.fingerId)) continue;
                if (TouchStick.IsMoveSide(t.position, Screen.width)) { if (moveId < 0) { moveId = t.fingerId; moveOrigin = t.position; } }
                else if (lookId < 0) { lookId = t.fingerId; lookLast = t.position; }
            }
            else if (t.fingerId == moveId)
            {
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) moveId = -1;
                else
                {
                    float r = stickRadius / Scale;
                    Move = TouchStick.Evaluate(moveOrigin, t.position, r);
                    knob.anchoredPosition = (TouchStick.Knob(moveOrigin, t.position, r) - moveOrigin) * Scale;
                }
            }
            else if (t.fingerId == lookId)
            {
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) lookId = -1;
                else { Look += TouchStick.Look(t.position - lookLast, Screen.height); lookLast = t.position; }
            }
        }
        if (moveId < 0) { Move = Vector2.zero; if (knob) knob.anchoredPosition = Vector2.zero; }
        else if (ring) ring.anchoredPosition = moveOrigin * Scale;
        if (!Active) return;
        Show(true);
        // the button mirrors the on-screen [E] prompt
        var ui = InteriorUI.Instance;
        string p = ui ? ui.PromptText : "";
        button.gameObject.SetActive(!string.IsNullOrEmpty(p));
        buttonLabel.text = string.IsNullOrEmpty(p) ? "" : p.Replace("[E] ", "");
    }
}
