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
core.bf_eval.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(C.c_uint64)]
core.bf_eval.restype=C.c_int

def evaluate(data,payload=b''):
    result=C.c_uint64(999)
    status=core.bf_eval(data,len(data),payload,len(payload),C.byref(result))
    return status,result.value

def program(*instructions):
    return struct.pack('<4sHHII',b'BFG1',1,0,len(instructions),0)+b''.join(struct.pack('<B7xQ',op,arg) for op,arg in instructions)

def verify(data):
    info=Info()
    result=core.bf_verify(data,len(data),C.byref(info))
    return result,info

class Verify(unittest.TestCase):
    def test_control_flow(self):
        rows=((1,1),(22,4),(1,7),(21,5),(1,9),(23,0))
        self.assertEqual(verify(program(*rows))[0],0)
        for bad in (
            ((1,1),(21,1),(23,0)),
            ((1,1),(21,99),(23,0)),
            ((22,2),(1,1),(23,0)),
            ((1,1),(21,3),(1,2),(23,0)),
            ((1,1),(22,5),(1,1),(1,2),(21,6),(2,0),(23,0)),
        ):
            self.assertEqual(verify(program(*bad))[0],1)
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

class Execute(unittest.TestCase):
    def test_scalars(self):
        mask=(1<<64)-1
        for op,expected in ((7,3&5),(8,3|5),(9,3^5),(10,3<<5),(11,3>>5),(12,8),(13,(3-5)&mask),(14,0),(15,1),(16,1),(17,1),(18,0),(19,0)):
            self.assertEqual(evaluate(program((1,3),(1,5),(op,0),(23,0))),(0,expected))
        self.assertEqual(evaluate(program((2,0),(23,0)),b'abc'),(0,3))
        for op in (10,11): self.assertEqual(evaluate(program((1,7),(1,64),(op,0),(23,0))),(0,0))
        self.assertEqual(evaluate(program((1,0),(20,0),(23,0))),(0,1))
        self.assertEqual(evaluate(program((1,0),(24,0),(23,0))),(0,mask))
        self.assertEqual(evaluate(b'bad'),(1,0))

if __name__=='__main__': unittest.main()
