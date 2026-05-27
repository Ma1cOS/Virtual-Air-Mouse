# ============================================================
#  MouseOutput: εικονικό ποντίκι μέσω evdev/UInput
# -----------------------------------------------------------
#  Απευθείας επικοινωνία με τον πυρήνα (/dev/uinput).
#  Λειτουργεί σε X11 και Wayland — μιλάει στον πυρήνα, όχι στον compositor.
#
#  Απαιτήσεις:
#    - pip install evdev
#    - χρήστης στην ομάδα uinput
#    - /dev/uinput προσβάσιμο
# ============================================================

try:
    from evdev import UInput, ecodes as _ecodes
    _evdev_ok = True
except Exception:
    UInput = None
    _ecodes = None
    _evdev_ok = False


class MouseOutput:
    """
    Εικονική συσκευή ποντικιού μέσω evdev/UInput.
    Παρέχει σχετική κίνηση (REL_X/REL_Y).

    Αν το evdev δεν είναι διαθέσιμο, όλες οι μέθοδοι γίνονται no-op.
    """

    def __init__(self):
        self._device = None
        self._ok = False
        if _evdev_ok:
            self._create()

    def _create(self):
        try:
            self._device = UInput({
                _ecodes.EV_REL: [
                    _ecodes.REL_X, _ecodes.REL_Y,
                ],
                _ecodes.EV_KEY: [
                    _ecodes.BTN_LEFT,
                ],
            }, name="virtual-air-mouse", version=0x3)
            self._ok = True
        except Exception:
            self._device = None
            self._ok = False

    @property
    def ok(self) -> bool:
        return self._ok

    @property
    def device_path(self):
        if self._device:
            # If the library supports it, grab it; otherwise return a placeholder string
            try:
                if self._device.device:
                    return self._device.device.path
            except AttributeError:
                pass
            return "/dev/uinput (Virtual)"
        return None

    def move(self, dx: int, dy: int):
        """
        Σχετική κίνηση κέρσορα, στέλνει REL_X/REL_Y.
        Η κλιμάκωση γίνεται από τον orchestrator (DELTA_SCALE).

        @param dx: μονάδες REL_X
        @param dy: μονάδες REL_Y
        """
        if not self._ok:
            return
        self._device.write(_ecodes.EV_REL, _ecodes.REL_X, dx)
        self._device.write(_ecodes.EV_REL, _ecodes.REL_Y, dy)
        self._device.syn()

    def close(self):
        """Απελευθέρωση της εικονικής συσκευής."""
        if self._device:
            self._device.close()
        self._device = None
        self._ok = False
