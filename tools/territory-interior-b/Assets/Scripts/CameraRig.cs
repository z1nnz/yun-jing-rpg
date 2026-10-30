using UnityEngine;

/// Third-person action-RPG camera: orbits a pivot above the player's shoulders (mouse to look, wheel to zoom),
/// pulls in when a wall or the ceiling is in the way, and hands over to an item's close-up while that item
/// holds the camera (chest / furnace panel open, lying in bed). useOverride gives the director a free shot.
public class CameraRig : MonoBehaviour
{
    public Transform target;
    public Interactable[] shots;
    public float yaw, pitch = 14f, distance = 2.6f;          // follow orbit (play: mouse / wheel; demo: director)
    public float minPitch = -20f, maxPitch = 65f, minDistance = 1.1f, maxDistance = 4.2f;
    public float pivotHeight = 1.15f, collideRadius = .2f, followFov = 50f, sensitivity = 2.4f;
    public bool autoBehind;                                  // ease yaw behind the player's facing while it moves
    public bool useOverride;                                 // director's free shot
    public Vector3 focusOverride;
    public float targetDistance = 6.2f, targetYaw, targetPitch = 42f, targetFov = 40f;

    Vector3 focus; float curDist, curYaw, curPitch, curFov, pulledDist; bool init;
    Camera cam;

    void LateUpdate()
    {
        if (DemoDirector.Driving) return;
        bool panel = InteriorUI.Instance && (InteriorUI.Instance.StorageOpen || InteriorUI.Instance.AlchemyOpen);
        var touch = TouchControls.Instance;
        bool touching = touch && touch.Active;
        bool free = panel || touching || Input.GetKey(KeyCode.LeftAlt);
        Cursor.lockState = free ? CursorLockMode.None : CursorLockMode.Locked; Cursor.visible = free;
        if (touching)
        {
            yaw += touch.Look.x;
            pitch = Mathf.Clamp(pitch + touch.Look.y, minPitch, maxPitch);
        }
        else if (!free)
        {
            yaw += Input.GetAxis("Mouse X") * sensitivity;
            pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * sensitivity, minPitch, maxPitch);
        }
        distance = Mathf.Clamp(distance - Input.mouseScrollDelta.y * .25f, minDistance, maxDistance);
        Tick(Time.deltaTime);
    }

    Interactable Holder()
    {
        if (shots != null) foreach (var s in shots) if (s && s.HoldsCamera) return s;
        return null;
    }

    public void Tick(float dt)
    {
        if (!cam) cam = GetComponent<Camera>();
        Vector3 wantFocus; float wantDist, wantYaw, wantPitch, wantFov, rate;
        var h = Holder();
        if (h != null) { wantFocus = h.shotFocus; wantDist = h.shotDistance; wantYaw = h.shotYaw; wantPitch = h.shotPitch; wantFov = h.shotFov; rate = 2.6f; }
        else if (useOverride) { wantFocus = focusOverride; wantDist = targetDistance; wantYaw = targetYaw; wantPitch = targetPitch; wantFov = targetFov; rate = 2.2f; }
        else
        {
            if (autoBehind && target) yaw = Mathf.LerpAngle(yaw, target.eulerAngles.y, 1f - Mathf.Exp(-dt * 1.6f));
            wantFocus = target.position + Vector3.up * pivotHeight; wantDist = distance; wantYaw = yaw; wantPitch = pitch; wantFov = followFov;
            rate = 5f;
        }
        float k = init ? 1f - Mathf.Exp(-dt * rate) : 1f;
        float ka = init ? 1f - Mathf.Exp(-dt * Mathf.Min(rate, 3.2f)) : 1f;
        focus = Vector3.Lerp(focus, wantFocus, k);
        curDist = Mathf.Lerp(curDist, wantDist, ka);
        curYaw = Mathf.LerpAngle(curYaw, wantYaw, ka);
        curPitch = Mathf.Lerp(curPitch, wantPitch, ka);
        curFov = Mathf.Lerp(curFov, wantFov, ka);
        init = true;

        Quaternion r = Quaternion.Euler(curPitch, curYaw, 0f);
        Vector3 back = -(r * Vector3.forward);
        // wall / ceiling avoidance: snap in at once, ease back out
        float allowed = curDist;
        Physics.SyncTransforms();
        if (Physics.SphereCast(focus, collideRadius, back, out var hit, curDist, ~0, QueryTriggerInteraction.Ignore))
            allowed = Mathf.Max(.35f, hit.distance - .05f);
        pulledDist = allowed < pulledDist || pulledDist <= 0f ? allowed : Mathf.Lerp(pulledDist, allowed, 1f - Mathf.Exp(-dt * 3f));
        transform.position = focus + back * pulledDist;
        transform.rotation = r;
        if (cam) cam.fieldOfView = curFov;
    }

    /// Ground-plane forward of the current view (for camera-relative movement).
    public Vector3 Forward => Quaternion.Euler(0f, curYaw, 0f) * Vector3.forward;
}
