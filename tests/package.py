"""Verify exact package members and run the extracted native deliverables."""
from hashlib import sha256
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('packaging',ROOT/'tools/package.py');packaging=importlib.util.module_from_spec(spec);spec.loader.exec_module(packaging)
platform=sys.argv[1];windows=platform=='windows-x64'
name=f'byteforge-0.2.0-preview-{platform}{".zip" if windows else ".tar.gz"}'
archive=ROOT/'dist'/name
assert (ROOT/'dist/SHA256SUMS.txt').read_text()==sha256(archive.read_bytes()).hexdigest()+'  '+name+'\n'
expected=packaging.entries(platform)
if windows:
    with ZipFile(archive) as stream:
        assert set(stream.namelist())==set(expected) and len(stream.namelist())==len(expected) and stream.testzip() is None
        values={name:stream.read(name) for name in expected}
else:
    with tarfile.open(archive,'r:gz') as stream:
        members=stream.getmembers();assert len(members)==len(expected) and {m.name for m in members}==set(expected) and all(m.isfile() for m in members)
        values={name:stream.extractfile(name).read() for name in expected}
folder=ROOT/'installed';folder.mkdir(exist_ok=True)
for name,value in values.items():
    source,mode=expected[name];assert value==packaging.content(source)
    target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value);target.chmod(mode)
binary=values['bin/byteforge.exe' if windows else 'bin/byteforge']
if windows:
    offset=struct.unpack_from('<I',binary,60)[0];assert binary[:2]==b'MZ' and binary[offset:offset+6]==b'PE\0\0\x64\x86'
else: assert binary[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',binary,18)[0]==62
subprocess.run([sys.executable,ROOT/'tests/integration.py',folder/('bin/byteforge.exe' if windows else 'bin/byteforge'),folder],check=True)
subprocess.run([sys.executable,ROOT/'tests/native.py',folder/('lib/byteforge.dll' if windows else 'lib/libbyteforge.so')],check=True)
compiler=sys.argv[2] if len(sys.argv)>2 else 'gcc'
consumer=folder/('embed.exe' if windows else 'embed')
subprocess.run([compiler,'-O2','-I',folder/'include',folder/'examples/embed.c',folder/'lib/libbyteforge.a','-o',consumer],check=True)
subprocess.run([consumer],check=True)
print('Native release package and extracted binaries verified')
