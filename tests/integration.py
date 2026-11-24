"""Native CLI round trips and malformed-capture checks."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

binary=Path(sys.argv[1]).resolve();root=Path(sys.argv[2]).resolve();checks=0
def run(*args,code=0):
    global checks
    result=subprocess.run([binary,*map(str,args)],capture_output=True,text=True,timeout=15)
    assert result.returncode==code,(args,result.returncode,result.stdout,result.stderr)
    checks+=1;return result.stdout
assert run('--version').strip()=='byteforge 0.2.0-preview'
assert 'Assembly' in run('--help')
with TemporaryDirectory() as directory:
    folder=Path(directory);program=folder/'tcp.bfg'
    compiled=json.loads(run('compile',root/'examples/tcp-syn.bf',program))
    assert compiled['instructions']>3
    assert json.loads(run('verify',program))['max_stack']<=64
    assert 'jz' in run('disasm',program)
    assert json.loads(run('run',program,root/'examples/tcp.bin'))['match']
    assert not json.loads(run('run',program,root/'examples/udp.bin',code=1))['match']
    report=json.loads(run('scan',program,root/'examples/traffic.pcap'))
    assert (report['packets'],report['matches'],report['indices'])==(2,1,[0])
    saved=program.read_bytes()
    run('compile',root/'examples/tcp-syn.bf',program,code=2)
    assert program.read_bytes()==saved
    source=folder/'invalid.bf';source.write_text('1 &&')
    missing=folder/'missing.bfg'
    run('compile',source,missing,code=2);assert not missing.exists()
    bad=folder/'bad.bfg';bad.write_bytes(saved[:-1]);run('verify',bad,code=2)
    capture=(root/'examples/traffic.pcap').read_bytes()
    for data in (b'',capture[:-1],b'bad!'+capture[4:],capture[:24]+b'x'):
        path=folder/'bad.pcap';path.write_bytes(data);assert run('scan',program,path,code=2)==''
    for endian,magic in (('<',0xa1b2c3d4),('>',0xa1b2c3d4),('<',0xa1b23c4d),('>',0xa1b23c4d)):
        packet=(root/'examples/tcp.bin').read_bytes()
        data=struct.pack(endian+'IHHIIII',magic,2,4,0,0,65535,1)+struct.pack(endian+'IIII',0,1,len(packet),len(packet))+packet
        path=folder/'portable.pcap';path.write_bytes(data)
        assert json.loads(run('scan',program,path))['matches']==1

    for endian,magic in (('<',0xa1b2c3d4),('>',0xa1b2c3d4),('<',0xa1b23c4d),('>',0xa1b23c4d)):
        for network,fcs in ((1, None),(1|0x24000000,4),(1|0x20000000,None),(1|0x04000000,0),(1|0xf4000000,30)):
            data=struct.pack(endian+'IHHIIII',magic,2,4,123,456,65535,network)+struct.pack(endian+'IIII',0,1,len(packet),len(packet))+packet
            path=folder/'fcs.pcap';path.write_bytes(data)
            report=json.loads(run('scan',program,path))
            assert report['link_type']==1 and report['fcs_bytes']==fcs,report
            assert report['raw_link_type']==network
        for reserved in (0x00010000,0x02000000,0x08000000):
            path.write_bytes(struct.pack(endian+'IHHIIII',magic,2,4,0,0,65535,1|reserved))
            assert run('scan',program,path,code=2)==''
    short=folder/'short.bin';short.write_bytes(b'x')
    assert not json.loads(run('run',program,short,code=1))['match']
    source.write_text('u64be(0)');unguarded=folder/'unguarded.bfg'
    run('compile',source,unguarded);run('run',unguarded,short,code=3)


    source.write_text('1 / (u8(0) - u8(0))');arithmetic=folder/'arithmetic.bfg'
    run('compile',source,arithmetic);assert run('run',arithmetic,root/'examples/tcp.bin',code=4)==''
    report=json.loads(run('scan',arithmetic,root/'examples/traffic.pcap',code=1))
    assert report['arithmetic_errors']==2 and report['matches']==0

# A reader that closes early must not receive a successful report exit status.
read_end,write_end=os.pipe();os.close(read_end)
with os.fdopen(write_end,'wb',buffering=0) as sink:
    closed=subprocess.run([binary,'--version'],stdout=sink,stderr=subprocess.PIPE,timeout=15)
assert closed.returncode==2,(closed.returncode,closed.stderr)
checks+=1
print(f'{checks} integration checks passed')
