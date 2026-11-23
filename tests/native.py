"""Native Assembly API regression tests; no compiler implementation in Python."""
import ctypes as C
from pathlib import Path
import struct
import sys
import unittest

LIBRARY=Path(sys.argv.pop(1)).resolve()
core=C.CDLL(str(LIBRARY))
class Info(C.Structure):
    _fields_=[('max_stack',C.c_uint32),('error_pc',C.c_uint32)]
core.bf_verify.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Info)]
core.bf_verify.restype=C.c_int

def program(*instructions):
    return struct.pack('<4sHHII',b'BFG1',1,0,len(instructions),0)+b''.join(struct.pack('<B7xQ',op,arg) for op,arg in instructions)

def verify(data):
    info=Info()
    result=core.bf_verify(data,len(data),C.byref(info))
    return result,info

class Verify(unittest.TestCase):
    def test_structure(self):
        data=program((1,7),(23,0))
        result,info=verify(data)
        self.assertEqual((result,info.max_stack,info.error_pc),(0,1,0xffffffff))
        for bad in (b'',data[:10],data[:-1],data+b'\0',b'bad!'+data[4:]):
            self.assertEqual(verify(bad)[0],1)
        for offset in (4,6,12,17):
            bad=bytearray(data);bad[offset]=2
            self.assertEqual(verify(bytes(bad))[0],1)
    def test_stack(self):
        self.assertEqual(verify(program((1,1),(1,2),(12,0),(23,0)))[1].max_stack,2)
        for rows in (((12,0),(23,0)),((1,1),(1,2),(23,0)),((1,1),),((1,1),(12,3),(23,0)),((1,1),(99,0),(23,0))):
            self.assertEqual(verify(program(*rows))[0],1)
        rows=[(1,0)]*65+[(12,0)]*64+[(23,0)]
        self.assertEqual(verify(program(*rows))[0],1)

if __name__=='__main__': unittest.main()
