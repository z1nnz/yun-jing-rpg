using UnityEngine;

/// Door curtain (TI07) hung from its top rail: whoever walks through the doorway pushes the cloth the way
/// they are walking, and it swings back and settles. Sits on a pivot at the rail; the curtain model is its child.
public class CurtainSway : MonoBehaviour
{
    public Transform walker;
    public float halfWidth = .7f, reach = .55f, pushDeg = 40f;
    public float stiffness = 38f, damping = 4.5f;
    float angle, vel, lastZ, dir = 1f;
    bool seen;

    void Update() { if (!DemoDirector.Driving) Tick(Time.deltaTime); }

    public void Tick(float dt)
    {
        float target = 0f;
        if (walker && dt > 0f)
        {
            Vector3 p = walker.position - transform.position;   // the rail runs along world x, the doorway along z
            if (seen && Mathf.Abs(p.z - lastZ) > 1e-4f) dir = Mathf.Sign(p.z - lastZ);
            lastZ = p.z; seen = true;
            if (Mathf.Abs(p.x) < halfWidth && Mathf.Abs(p.z) < reach)
                target = -pushDeg * (1f - Mathf.Abs(p.z) / reach) * dir;   // negative x-rotation swings the hem towards +z
        }
        float acc = stiffness * (target - angle) - damping * vel;
        vel += acc * dt; angle += vel * dt;
        transform.localRotation = Quaternion.Euler(angle, 0f, 0f);
    }
}
