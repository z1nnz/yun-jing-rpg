/// 旅途手札: the cover opens, spreads turn one at a time, the cover closes. Pure timing and state for the
/// book overlay; what is written on the pages comes later (blank pages for now). Input during an animation is ignored.
public sealed class Journal
{
    public enum Phase { Closed, Opening, Open, Turning, Closing }
    public const float OpenTime = .9f, TurnTime = .55f, CloseTime = .6f;

    /// Page count, rounded up to whole spreads (two pages per spread).
    public readonly int Pages;
    public int Spreads => Pages / 2;
    public Phase State { get; private set; } = Phase.Closed;
    /// 0-based spread on display; its left page is 2 * Spread + 1, its right page 2 * Spread + 2.
    public int Spread { get; private set; }
    /// +1 while a page turns forward, -1 while it turns back.
    public int TurnDir { get; private set; }
    /// 0..1 progress of the current animation.
    public float T { get; private set; }

    public Journal(int pages) { Pages = System.Math.Max(2, pages + pages % 2); }

    public bool Shown => State != Phase.Closed;
    public bool CanNext => State == Phase.Open && Spread < Spreads - 1;
    public bool CanPrev => State == Phase.Open && Spread > 0;

    public bool Open()
    {
        if (State != Phase.Closed) return false;
        State = Phase.Opening; Spread = 0; T = 0f;
        return true;
    }

    public bool Next() => Turn(+1, CanNext);
    public bool Prev() => Turn(-1, CanPrev);

    bool Turn(int dir, bool allowed)
    {
        if (!allowed) return false;
        State = Phase.Turning; TurnDir = dir; T = 0f;
        return true;
    }

    public bool Close()
    {
        if (State != Phase.Open) return false;
        State = Phase.Closing; T = 0f;
        return true;
    }

    public void Tick(float dt)
    {
        switch (State)
        {
            case Phase.Opening:
                if ((T += dt / OpenTime) >= 1f) { T = 1f; State = Phase.Open; }
                break;
            case Phase.Turning:
                if ((T += dt / TurnTime) >= 1f) { T = 1f; Spread += TurnDir; TurnDir = 0; State = Phase.Open; }
                break;
            case Phase.Closing:
                if ((T += dt / CloseTime) >= 1f) { T = 0f; Spread = 0; State = Phase.Closed; }
                break;
        }
    }
}
