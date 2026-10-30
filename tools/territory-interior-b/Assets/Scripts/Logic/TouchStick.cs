using UnityEngine;

/// Landscape touch layout rules, kept free of scene objects so they can be tested:
/// a finger that lands on the left half drives a floating move stick, one on the right half turns the camera.
public static class TouchStick
{
    public const float DeadZone = .12f;

    public static bool IsMoveSide(Vector2 screenPos, float screenWidth) => screenPos.x < screenWidth * .5f;

    /// Move input from the stick origin to the finger: length 0…1, zero inside the dead zone,
    /// rescaled so it starts from 0 just outside it.
    public static Vector2 Evaluate(Vector2 origin, Vector2 finger, float radius)
    {
        if (radius <= 0f) return Vector2.zero;
        Vector2 d = (finger - origin) / radius;
        float m = d.magnitude;
        if (m <= DeadZone) return Vector2.zero;
        float k = Mathf.Min(1f, (m - DeadZone) / (1f - DeadZone));
        return d / m * k;
    }

    /// Where the knob is drawn: the finger, clamped to the stick ring.
    public static Vector2 Knob(Vector2 origin, Vector2 finger, float radius) => origin + Vector2.ClampMagnitude(finger - origin, radius);

    /// Camera turn (yaw, pitch degrees) from a right-half drag in pixels; a full screen-height drag turns 180°.
    public static Vector2 Look(Vector2 deltaPixels, float screenHeight) =>
        screenHeight <= 0f ? Vector2.zero : new Vector2(deltaPixels.x, -deltaPixels.y) * (180f / screenHeight);
}
