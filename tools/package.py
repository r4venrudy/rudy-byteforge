"""Package a tested native build with deterministic archive metadata."""
from argparse import ArgumentParser
import gzip
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tarfile
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0-preview'
def entries(platform):
    windows=platform=='windows-x64'
    files={'bin/'+('byteforge.exe' if windows else 'byteforge'):(ROOT/'build'/('byteforge.exe' if windows else 'byteforge'),0o755),
           'lib/'+('byteforge.dll' if windows else 'libbyteforge.so'):(ROOT/'build'/('byteforge.dll' if windows else 'libbyteforge.so'),0o755),
           'lib/libbyteforge.a':(ROOT/'build/libbyteforge.a',0o644)}
    for name in ('README.md','LICENSE','docs/FORMAT.md','include/byteforge.h','assets/banner.svg'):
        files[name]=(ROOT/name,0o644)
    for path in (ROOT/'examples').iterdir(): files[path.relative_to(ROOT).as_posix()]=(path,0o644)
    return files
def content(path):
    value=path.read_bytes()
    return value.replace(b'\r\n',b'\n') if path.suffix in ('.md','.svg','.h','.bf','.c') or path.name=='LICENSE' else value
def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--platform',choices=('windows-x64','linux-x64'),required=True);args=parser.parse_args()
    folder=ROOT/'dist';folder.mkdir(exist_ok=True)
    path=folder/f'byteforge-{VERSION}-{args.platform}{".zip" if args.platform=="windows-x64" else ".tar.gz"}'
    files=entries(args.platform)
    if path.suffix=='.zip':
        with ZipFile(path,'w') as archive:
            for name,(source,mode) in sorted(files.items()):
                info=ZipInfo(name,(2020,1,1,0,0,0));info.create_system=3;info.external_attr=(0o100000|mode)<<16
                archive.writestr(info,content(source),compress_type=ZIP_DEFLATED,compresslevel=9)
    else:
        with path.open('wb') as stream,gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as compressed:
            with tarfile.open(fileobj=compressed,mode='w',format=tarfile.USTAR_FORMAT) as archive:
                for name,(source,mode) in sorted(files.items()):
                    value=content(source);info=tarfile.TarInfo(name);info.mode=mode;info.size=len(value);archive.addfile(info,BytesIO(value))
    (folder/'SHA256SUMS.txt').write_bytes((sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n').encode('ascii'))
    print(path)
if __name__=='__main__': main()
