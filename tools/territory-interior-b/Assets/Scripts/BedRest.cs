using UnityEngine;

/// Bed: E lies the player down on the mattress, E again gets up.
/// Once lying, the quilt unrolls from the foot of the bed up to the shoulders (the head stays out);
/// the folded quilt at the foot hides while the spread one is in use.
public class BedRest : Interactable
{
    public Vector3 liePosition;      // world position of the avatar pivot while lying
    public Quaternion lieRotation;   // world rotation of the avatar while lying
    public Vector3 headDir = Vector3.forward, sideOut = Vector3.right;   // along the bed towards the pillow; from the bed towards the room
    public float mattressTop = .6f, halfWidth = .6f;
    public Transform quiltPivot;     // spread quilt, pivot on the foot edge, local +Z runs towards the head
    public GameObject foldedQuilt;
    PlayerAvatar occupant;
    float cover;

    public override string Prompt => "[E] 躺下休息";
    public override bool HoldsCamera => occupant != null && occupant.IsLying;

    public override void Interact(PlayerAvatar player)
    {
        if (player.IsLying) player.GetUp();
        else { player.LieDown(this); occupant = player; }
    }

    public override void Tick(float dt)
    {
        bool want = occupant != null && occupant.Resting;
        cover = Mathf.MoveTowards(cover, want ? 1f : 0f, dt / (want ? .8f : .45f));
        if (occupant != null && !occupant.IsLying && cover <= 0f) occupant = null;
        float s = cover * cover * (3f - 2f * cover);
        if (quiltPivot)
        {
            quiltPivot.gameObject.SetActive(cover > .001f);
            quiltPivot.localScale = new Vector3(1f, Mathf.Lerp(.4f, 1f, s), Mathf.Lerp(.06f, 1f, s));
        }
        if (foldedQuilt) foldedQuilt.SetActive(cover < .15f);
    }
}
