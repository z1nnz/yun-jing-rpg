using System.Collections.Generic;
using UnityEngine;

/// The player character: walk/idle by sampling the QPlayerMale v006 clips, plus a staged get-into-bed move.
/// The rig has no lie-down clip, so getting into bed is posed in code on top of the Idle frame:
/// turn and sit on the bed edge (thighs / knees bent) → swing the legs onto the bed → lie back.
/// Getting up plays the same stages backwards. The character FBX is not modified.
public class PlayerAvatar : MonoBehaviour
{
    public GameObject model;            // imported QPlayerMale instance (child)
    public AnimationClip idleClip, walkClip;
    public float walkSpeed = 1.25f, turnSpeed = 540f;
    public float lieDownSeconds = 2.6f, getUpSeconds = 2.2f;
    public List<ItemStack> inventory = new List<ItemStack>();
    public int bagCapacity = 15;

    float animTime, lieT, lieDir;
    bool movedThisFrame;
    Vector3 standPos; Quaternion standRot;
    BedRest bed;
    Transform thighL, thighR, calfL, calfR, pelvis;
    float hipH;                         // pelvis height above the root while standing

    public bool IsLying => lieT > .5f || lieDir > 0f;
    public bool Resting => lieT >= 1f && lieDir == 0f;
    public bool Busy => (lieDir > 0f && lieT < 1f) || (lieDir < 0f && lieT > 0f);

    void Update()
    {
        if (!DemoDirector.Driving) Tick(Time.deltaTime);
    }

    /// Move along the ground plane; dir need not be normalised (length > 1 is clamped).
    public void Move(Vector3 dir, float dt)
    {
        if (lieT > 0f) return;
        dir.y = 0f;
        if (dir.sqrMagnitude < 1e-6f) return;
        if (dir.magnitude > 1f) dir.Normalize();
        transform.position += dir * walkSpeed * dt;
        Face(dir, dt);
        movedThisFrame = true;
    }

    public void Face(Vector3 dir, float dt)
    {
        dir.y = 0f;
        if (dir.sqrMagnitude < 1e-6f) return;
        transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(dir), turnSpeed * dt);
    }

    public void LieDown(BedRest b)
    {
        if (lieT > 0f) return;
        FindBones();
        bed = b; standPos = transform.position; standRot = transform.rotation; lieDir = 1f;
        if (idleClip) idleClip.SampleAnimation(model, 0f);
        hipH = pelvis ? Vector3.Dot(pelvis.position - transform.position, transform.up) : .45f;
        if (InteriorUI.Instance) InteriorUI.Instance.Toast("躺下休息……");
    }

    public void GetUp()
    {
        if (bed == null) return;
        lieDir = -1f;
        if (InteriorUI.Instance) InteriorUI.Instance.Toast("起身");
    }

    void FindBones()
    {
        if (pelvis) return;
        foreach (var t in model.GetComponentsInChildren<Transform>())
            switch (t.name)
            {
                case "pelvis": pelvis = t; break;
                case "thigh_l": thighL = t; break;
                case "thigh_r": thighR = t; break;
                case "calf_l": calfL = t; break;
                case "calf_r": calfR = t; break;
            }
    }

    static float Smooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

    /// Hip point, body rotation and joint bends (degrees) along the get-into-bed path, u = 0 standing … 1 lying.
    void LiePose(float u, out Vector3 hip, out Quaternion rot, out float thigh, out float knee)
    {
        const float A = .32f, B = .6f;
        Vector3 head = bed.headDir, outDir = bed.sideOut;
        Vector3 hipLie = bed.liePosition + head * hipH;                       // lying: body axis along the bed
        float seat = bed.mattressTop + .13f;
        Vector3 hipMid = new Vector3(hipLie.x, seat, hipLie.z);
        Vector3 hipEdge = hipMid + outDir * (bed.halfWidth - .16f);
        Vector3 hipStand = standPos + Vector3.up * hipH;
        Quaternion rOut = Quaternion.LookRotation(outDir), rFoot = Quaternion.LookRotation(-head);
        if (u < A)
        {
            // turn round and hop up to sit on the edge
            float s = Smooth(u / A);
            hip = Vector3.Lerp(hipStand, hipEdge, s) + Vector3.up * Mathf.Sin(s * Mathf.PI) * .12f;
            rot = Quaternion.Euler(0f, Mathf.LerpAngle(standRot.eulerAngles.y, rOut.eulerAngles.y, s), 0f);
            thigh = 90f * s; knee = 90f * s;
        }
        else if (u < B)
        {
            // swing the legs up onto the bed, straightening the knees
            float s = Smooth((u - A) / (B - A));
            hip = Vector3.Lerp(hipEdge, hipMid, s);
            rot = Quaternion.Slerp(rOut, rFoot, s);
            thigh = 90f; knee = 90f * (1f - s);
        }
        else
        {
            // lie back onto the pillow
            float s = Smooth((u - B) / (1f - B));
            hip = Vector3.Lerp(hipMid, hipLie, s);
            rot = Quaternion.Slerp(rFoot, bed.lieRotation, s);
            thigh = 90f * (1f - s); knee = 0f;
        }
    }

    public void Tick(float dt)
    {
        animTime += dt;
        float thigh = 0f, knee = 0f;
        if (lieDir != 0f || lieT > 0f)
        {
            lieT = Mathf.Clamp01(lieT + lieDir * dt / (lieDir > 0f ? lieDownSeconds : getUpSeconds));
            if (bed != null)
            {
                LiePose(lieT, out var hip, out var rot, out thigh, out knee);
                transform.SetPositionAndRotation(hip - rot * (Vector3.up * hipH), rot);
                if (lieT <= 0f) transform.SetPositionAndRotation(standPos, standRot);
            }
            if (lieDir < 0f && lieT <= 0f) { lieDir = 0f; bed = null; }
            else if (lieDir > 0f && lieT >= 1f) lieDir = 0f;
        }
        var clip = movedThisFrame && walkClip ? walkClip : idleClip;
        if (clip && model)
        {
            float t = lieT > 0f ? 0f : animTime % clip.length;
            clip.SampleAnimation(model, t);
        }
        // bend hips and knees about the body's side axis (thigh swings forward, shin folds back down)
        if (thigh > .01f || knee > .01f)
        {
            Vector3 side = transform.right;
            foreach (var th in new[] { thighL, thighR }) if (th) th.rotation = Quaternion.AngleAxis(-thigh, side) * th.rotation;
            foreach (var ca in new[] { calfL, calfR }) if (ca) ca.rotation = Quaternion.AngleAxis(knee, side) * ca.rotation;
        }
        movedThisFrame = false;
    }
}
