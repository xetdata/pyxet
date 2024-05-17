import ctypes
import os
from .. import rpyxet 
sopath = os.path.dirname(__file__)

xlibpath = os.path.join(sopath, "libhooks.so")

_xlib = ctypes.cdll.LoadLibrary(xlibpath)

_xlib.set_xlog_point.argtypes = [ctypes.c_char_p]
_xlib.set_xlog_point.restype = ctypes.c_int
_xlib.get_xlog_point.argtypes = []
_xlib.get_xlog_point.restype = ctypes.c_char_p
_xlib.close_xlog_point.argtypes = []
_xlib.close_xlog_point.restype = ctypes.c_int
_xlib.write_xlog.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
_xlib.write_xlog.restype = ctypes.c_int

def set_xlog_point(f):
    if os.path.isabs(f) == False:
        f = os.path.abspath(f)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    cs = ctypes.c_char_p(bytes(f, 'utf-8'))
    ret = int(_xlib.set_xlog_point(cs))
    if ret != 0:
        return ctypes.get_errno()
    return 0

def get_xlog_point():
    return _xlib.get_xlog_point().decode('utf-8')

def close_xlog_point():
    ret = int(_xlib.close_xlog_point())
    if ret != 0:
        return ctypes.get_errno()
    return 0

def write_xlog(s):
    b = bytes(s + "\n", 'utf-8')
    cs = ctypes.c_char_p(b)
    ret = int(_xlib.write_xlog(cs, len(b)))
    if ret != 0:
        return ctypes.get_errno()
    return 0
