"""Windows timer resolution fix. The DeepFilterNet plugin's threads sleep in small steps; with Windows'
default 15.6 ms timer they wake too late, fall behind real time, and the plugin eventually aborts.
Windows 11 only honours a 1 ms timer request for processes that opt out of timer throttling."""
import ctypes
from ctypes import wintypes


class _PPTS(ctypes.Structure):
    _fields_ = [('Version', wintypes.ULONG), ('ControlMask', wintypes.ULONG), ('StateMask', wintypes.ULONG)]


def enable_1ms_timer():
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.SetProcessInformation.restype = wintypes.BOOL
    st = _PPTS(1, 0x4, 0)  # PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION: control it, state off
    ok = k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(st), ctypes.sizeof(st))
    ctypes.windll.winmm.timeBeginPeriod(1)
    return bool(ok)


def current_resolution_ms():
    nt = ctypes.WinDLL('ntdll')
    mn, mx, cur = wintypes.ULONG(), wintypes.ULONG(), wintypes.ULONG()
    nt.NtQueryTimerResolution(ctypes.byref(mn), ctypes.byref(mx), ctypes.byref(cur))
    return cur.value / 10000
