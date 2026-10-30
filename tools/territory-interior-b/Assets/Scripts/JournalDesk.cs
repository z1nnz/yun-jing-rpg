using UnityEngine;

/// 旅途手札 on the desk (TI03): E frames the book on the desk, then the book overlay opens on screen —
/// cover swings open, pages turn with ← → (or the buttons), Esc / E / 合上 closes it. Page text is empty for now;
/// pageText is where the written pages go once the content is ready.
public class JournalDesk : Interactable
{
    public string[] pageText = new string[8];
    public float lookDelay = .6f;          // camera settles on the desk before the book comes up
    public bool isOpen;
    public Journal book;
    float wait;

    public override string Prompt => isOpen ? "" : "[E] 翻開旅途手札";
    public override bool HoldsCamera => isOpen;

    Journal Book => book ??= new Journal(pageText.Length);

    public override void Interact(PlayerAvatar player)
    {
        if (isOpen) return;
        isOpen = true; wait = lookDelay;
        if (InteriorUI.Instance) InteriorUI.Instance.ShowJournal(this);
    }

    public void Next() => Book.Next();
    public void Prev() => Book.Prev();
    public void Close() { if (!Book.Close() && Book.State == Journal.Phase.Closed) Finish(); }

    void Finish()
    {
        isOpen = false;
        if (InteriorUI.Instance) InteriorUI.Instance.HideJournal();
    }

    public string PageText(int page) => page >= 1 && page <= pageText.Length ? pageText[page - 1] ?? "" : "";

    public override void Tick(float dt)
    {
        if (!isOpen) return;
        if (wait > 0f) { if ((wait -= dt) <= 0f) Book.Open(); return; }
        bool wasShown = Book.Shown;
        Book.Tick(dt);
        if (wasShown && !Book.Shown) Finish();
    }
}
