"""Native Assembly API regression tests; no compiler implementation in Python."""
import ctypes as C
from pathlib import Path
import struct
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

LIBRARY=Path(sys.argv.pop(1)).resolve()
core=C.CDLL(str(LIBRARY))
class Info(C.Structure):
    _fields_=[('max_stack',C.c_uint32),('error_pc',C.c_uint32)]
core.bf_verify.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Info)]
core.bf_verify.restype=C.c_int
core.bf_eval.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(C.c_uint64)]
core.bf_eval.restype=C.c_int
class CompileInfo(C.Structure):
    _fields_=[('size',C.c_size_t),('error_offset',C.c_uint32),('reserved',C.c_uint32)]
core.bf_compile.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(CompileInfo)]
core.bf_compile.restype=C.c_int

def compile_source(text,capacity=16400):
    text=text.encode() if isinstance(text,str) else text
    output=C.create_string_buffer(max(capacity,1));info=CompileInfo()
    status=core.bf_compile(text,len(text),output,capacity,C.byref(info))
    return status,output.raw[:info.size],info.error_offset

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
    def test_profile_boundaries(self):
        longest=program((1,1),*([(20,0)]*1022),(23,0))
        self.assertEqual(verify(longest)[0],0)
        self.assertEqual(evaluate(longest),(0,1))
        self.assertEqual(verify(program((1,1),*([(20,0)]*1023),(23,0)))[0],1)
        deepest=program(*([(1,1)]*64),*([(12,0)]*63),(23,0))
        self.assertEqual(verify(deepest)[1].max_stack,64)
        self.assertEqual(evaluate(deepest),(0,64))
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
    def test_branches_and_short_circuit(self):
        for condition,expected in ((0,9),(1,7),(42,7)):
            rows=((1,condition),(22,4),(1,7),(21,5),(1,9),(23,0))
            self.assertEqual(evaluate(program(*rows)),(0,expected))
        guarded=program((2,0),(1,8),(19,0),(22,6),(6,0),(21,7),(1,0),(23,0))
        self.assertEqual(evaluate(guarded,b'x'),(0,0))
        self.assertEqual(evaluate(guarded,b'abcdefgh'),(0,int.from_bytes(b'abcdefgh','big')))
    def test_bounded_loads(self):
        payload=bytes(range(1,17))
        for op,width in ((3,1),(4,2),(5,4),(6,8)):
            for offset in (0,1,len(payload)-width):
                expected=int.from_bytes(payload[offset:offset+width],'big')
                self.assertEqual(evaluate(program((op,offset),(23,0)),payload),(0,expected))
            for offset in (len(payload)-width+1,len(payload),(1<<64)-1):
                self.assertEqual(evaluate(program((op,offset),(23,0)),payload),(2,0))
        self.assertEqual(evaluate(program((3,0),(23,0))),(2,0))
    def test_scalars(self):
        mask=(1<<64)-1
        for op,expected in ((7,3&5),(8,3|5),(9,3^5),(10,3<<5),(11,3>>5),(12,8),(13,(3-5)&mask),(14,0),(15,1),(16,1),(17,1),(18,0),(19,0)):
            self.assertEqual(evaluate(program((1,3),(1,5),(op,0),(23,0))),(0,expected))
        self.assertEqual(evaluate(program((2,0),(23,0)),b'abc'),(0,3))
        for op in (10,11): self.assertEqual(evaluate(program((1,7),(1,64),(op,0),(23,0))),(0,0))
        self.assertEqual(evaluate(program((1,0),(20,0),(23,0))),(0,1))
        self.assertEqual(evaluate(program((1,0),(24,0),(23,0))),(0,mask))
        self.assertEqual(evaluate(b'bad'),(1,0))

class Compile(unittest.TestCase):

    def test_arithmetic_3(self):
        status,data,position=compile_source('3*7')
        self.assertEqual(status,0,position)
        self.assertEqual(evaluate(data),(0,21))
        status,data,position=compile_source('2+3*4')
        self.assertEqual(status,0,position)
        self.assertEqual(evaluate(data),(0,14))
        status,data,position=compile_source('0xffffffffffffffff*2')
        self.assertEqual(status,0,position)
        self.assertEqual(evaluate(data),(0,18446744073709551614))


    def test_little_endian_64(self):
        status,data,position=compile_source('u64le(1)')
        self.assertEqual(status,0,position)
        self.assertEqual(verify(data)[0],0)
        for size in range(11):
            payload=bytes(range(1,size+1))
            expected=(0,int.from_bytes(payload[1:1+8],'little')) if size>=1+8 else (2,0)
            self.assertEqual(evaluate(data,payload),expected)
            self.assertEqual(evaluate(program((27,1),(23,0)),payload),expected)
        self.assertEqual(evaluate(program((27,(1<<64)-1),(23,0)),b'abcdefgh'),(2,0))


    def test_little_endian_32(self):
        status,data,position=compile_source('u32le(1)')
        self.assertEqual(status,0,position)
        self.assertEqual(verify(data)[0],0)
        for size in range(11):
            payload=bytes(range(1,size+1))
            expected=(0,int.from_bytes(payload[1:1+4],'little')) if size>=1+4 else (2,0)
            self.assertEqual(evaluate(data,payload),expected)
            self.assertEqual(evaluate(program((26,1),(23,0)),payload),expected)
        self.assertEqual(evaluate(program((26,(1<<64)-1),(23,0)),b'abcdefgh'),(2,0))


    def test_little_endian_16(self):
        status,data,position=compile_source('u16le(1)')
        self.assertEqual(status,0,position)
        self.assertEqual(verify(data)[0],0)
        for size in range(11):
            payload=bytes(range(1,size+1))
            expected=(0,int.from_bytes(payload[1:1+2],'little')) if size>=1+2 else (2,0)
            self.assertEqual(evaluate(data,payload),expected)
            self.assertEqual(evaluate(program((25,1),(23,0)),payload),expected)
        self.assertEqual(evaluate(program((25,(1<<64)-1),(23,0)),b'abcdefgh'),(2,0))

    def test_capacity_and_reentrancy(self):
        for capacity,status in ((0,4),(15,4),(16,4),(47,4),(48,0),(49,0)):
            buffer=C.create_string_buffer(b'X'*96,96);info=CompileInfo()
            result=core.bf_compile(b'1',1,buffer,capacity,C.byref(info))
            self.assertEqual(result,status)
            self.assertEqual(buffer.raw[capacity:],b'X'*(96-capacity))
            if status: self.assertEqual(info.size,0)
        self.assertEqual(compile_source(' '*8193)[0],3)
        self.assertEqual(compile_source('1'+'+1'*1023)[0],4)
        def work(index):
            text=f'len >= 1 && (u8(0) + {index}) == {index+7}'
            status,data,_=compile_source(text)
            return status,evaluate(data,b'\x07')
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(item==(0,(0,1)) for item in pool.map(work,range(400))))
    def test_short_circuit(self):
        for text,value in (('0 && u64be(0)',0),('1 || u64be(0)',1),('7 && 8',1),('0 || 7',1),('2 || 3 && 0',1),('0 || 1 && 0',0),('len >= 2 && u16be(0) == 0x1234',0)):
            status,data,position=compile_source(text)
            self.assertEqual(status,0,(text,position))
            self.assertEqual(verify(data)[0],0,text)
            self.assertEqual(evaluate(data),(0,value),text)
        for text in ('1 && u8(0)','0 || u8(0)'):
            status,data,_=compile_source(text)
            self.assertEqual(status,0)
            self.assertEqual(evaluate(data),(2,0))
    def test_precedence_and_loads(self):
        for text,value in (('1+2-3',0),('2+3<<2',20),('1|2&4',1),('1+2==3',1),('-1',(1<<64)-1),('~0',(1<<64)-1),('!!7',1),('u16be(1)',0x0203),('len-u8(0)',7),('(7^2)&3',1),('0xffffffffffffffff+1',0)):
            status,data,position=compile_source(text)
            self.assertEqual(status,0,(text,position))
            self.assertEqual(verify(data)[0],0,text)
            self.assertEqual(evaluate(data,bytes(range(1,9))),(0,value),text)
        for text in ('1+','1 2','(1','1)','u8(1+2)','u8(-1)','u8()', '('*40+'1'+')'*40, '!'*70+'1'):
            self.assertEqual(compile_source(text)[0],3,text)
    def test_literals(self):
        for text,value in (('0',0),('18446744073709551615',(1<<64)-1),('0xFF',255),('  len\n',3)):
            status,data,_=compile_source(text)
            self.assertEqual(status,0)
            self.assertEqual(verify(data)[0],0)
            self.assertEqual(evaluate(data,b'abc'),(0,value))
        for text in ('','0x','18446744073709551616','0x10000000000000000','unknown','1\x00'):
            self.assertEqual(compile_source(text)[0],3)
        self.assertEqual(compile_source('1',16)[0],4)

if __name__=='__main__': unittest.main()
