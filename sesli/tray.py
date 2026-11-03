"""Tray icon: closing the window hides Sesli to the tray (it keeps processing); Quit is in the tray menu.
pystray runs its own thread, so its clicks are queued and handled on the Tk thread (Tray.poll)."""
import ctypes
import queue

from paths import res

SHOW_EVENT = 'Sesli.Show'  # a second launch sets this to bring the window back

try:
    import pystray
    from PIL import Image
except Exception:  # running from source without pystray/Pillow: the X button just quits
    pystray = None

k32 = ctypes.windll.kernel32


class Tray:
    def __init__(self, T):
        self.q = queue.Queue()
        self.icon = None
        self.noted = False
        self.show_ev = k32.CreateEventW(None, False, False, SHOW_EVENT)  # auto-reset
        if pystray is None:
            return
        menu = pystray.Menu(
            pystray.MenuItem(lambda _: T('tray_open'), lambda: self.q.put('show'), default=True),
            pystray.MenuItem(lambda _: T('tray_quit'), lambda: self.q.put('quit')))
        try:
            img = Image.open(res('assets', 'icon64.png'))
            self.icon = pystray.Icon('Sesli', img, 'Sesli', menu)
            self.icon.run_detached()
        except Exception:
            self.icon = None

    @property
    def available(self):
        return self.icon is not None

    def poll(self):
        """Pending actions: 'show' (tray click or a second launch) or 'quit'."""
        out = []
        if self.show_ev and k32.WaitForSingleObject(self.show_ev, 0) == 0:
            out.append('show')
        while True:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                return out

    def note_once(self, text):
        """First hide only: tell the user Sesli is still running down here."""
        if self.icon is not None and not self.noted:
            self.noted = True
            try:
                self.icon.notify(text, 'Sesli')
            except Exception:
                pass

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
