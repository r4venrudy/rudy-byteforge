"""Seeded independent expression evaluation and bytecode verification oracles."""
import ctypes as C
from pathlib import Path
import random
import struct
import sys

core=C.CDLL(str(Path(sys.argv[1]).resolve()))
class CI(C.Structure): _fields_=[('size',C.c_size_t),('offset',C.c_uint32),('reserved',C.c_uint32)]
core.bf_compile.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(CI)]
core.bf_verify.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p]
core.bf_eval.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.POINTER(C.c_uint64)]
rng=random.Random(0xB17EF09);MASK=(1<<64)-1
class Short(Exception): pass
def make(depth):
    if not depth or rng.random()<.25:
        kind=rng.choice(('const','len','load'))
        return (kind,rng.getrandbits(64) if kind=='const' else rng.randrange(45))
    if rng.random()<.15: return (rng.choice(('!','~','neg')),make(depth-1))
    return (rng.choice(('+','-','&','|','^','<<','>>','==','!=','<','<=','>','>=','&&','||')),make(depth-1),make(depth-1))
def source(node):
    op=node[0]
    if op=='const': return hex(node[1])
    if op=='len': return 'len'
    if op=='load': return f'u8({node[1]})'
    if len(node)==2: return '('+('-' if op=='neg' else op)+source(node[1])+')'
    return '('+source(node[1])+op+source(node[2])+')'
def reference(node,data):
    op=node[0]
    if op=='const': return node[1]
    if op=='len': return len(data)
    if op=='load':
        if node[1]>=len(data): raise Short()
        return data[node[1]]
    a=reference(node[1],data)
    if op=='!': return int(not a)
    if op=='~': return (~a)&MASK
    if op=='neg': return (-a)&MASK
    if op=='&&': return int(bool(a) and bool(reference(node[2],data)))
    if op=='||': return int(bool(a) or bool(reference(node[2],data)))
    b=reference(node[2],data)
    if op=='+': return (a+b)&MASK
    if op=='-': return (a-b)&MASK
    if op=='&': return a&b
    if op=='|': return a|b
    if op=='^': return a^b
    if op=='<<': return (a<<b)&MASK if b<64 else 0
    if op=='>>': return a>>b if b<64 else 0
    return int({'==':a==b,'!=':a!=b,'<':a<b,'<=':a<=b,'>':a>b,'>=':a>=b}[op])
def reference_valid(blob):
    if len(blob)<16: return False
    magic,version,flags,count,reserved=struct.unpack_from('<4sHHII',blob)
    if magic!=b'BFG1' or version!=1 or flags or reserved or not 1<=count<=1024 or len(blob)!=16+16*count: return False
    states={0:0}
    for pc in range(count):
        if pc not in states: return False
        op=blob[16+pc*16];arg=struct.unpack_from('<Q',blob,24+pc*16)[0];depth=states[pc]
        if any(blob[17+pc*16:24+pc*16]) or not 1<=op<=26: return False
        if op not in (1,3,4,5,6,21,22,25,26) and arg: return False
        if op in (1,2,3,4,5,6,25,26): depth+=1
        elif 7<=op<=19:
            if depth<2: return False
            depth-=1
        elif op in (20,24):
            if depth<1: return False
        elif op==22:
            if depth<1: return False
            depth-=1
        if depth>64: return False
        if op==23:
            if depth!=1 or pc!=count-1: return False
            continue
        targets=[] if op==21 else [pc+1]
        if op in (21,22):
            if not pc<arg<count: return False
            targets.append(arg)
        for target in targets:
            if target>=count or (target in states and states[target]!=depth): return False
            states[target]=depth
    return blob[16+(count-1)*16]==23

corpus=[]
for index in range(2500):
    tree=make(4);text=source(tree).encode();out=C.create_string_buffer(16400);info=CI()
    status=core.bf_compile(text,len(text),out,len(out),C.byref(info))
    assert status==0,(text,status,info.offset)
    blob=out.raw[:info.size];assert reference_valid(blob)
    payload=rng.randbytes(rng.randrange(41));actual=C.c_uint64(123)
    try: expected=(0,reference(tree,payload))
    except Short: expected=(2,0)
    result=core.bf_eval(blob,len(blob),payload,len(payload),C.byref(actual))
    assert (result,actual.value)==expected,(text,payload.hex(),expected,result,actual.value)
    if index<100: corpus.append(blob)
for index in range(5000):
    data=bytearray(rng.choice(corpus))
    for _ in range(rng.randrange(1,5)):
        mode=rng.randrange(3)
        if mode==0 and data: data[rng.randrange(len(data))]=rng.randrange(256)
        elif mode==1 and data: data=data[:rng.randrange(len(data))]
        else: data.extend(rng.randbytes(rng.randrange(5)))
    blob=bytes(data);expected=reference_valid(blob)
    assert (core.bf_verify(blob,len(blob),None)==0)==expected,(index,blob.hex())
print('2500 expression oracle cases and 5000 bytecode mutation oracle cases passed')
