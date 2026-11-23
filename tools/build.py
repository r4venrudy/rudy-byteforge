"""Assemble ByteForge's native core and link the optional C file interface."""
from argparse import ArgumentParser
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--nasm',default='nasm')
    parser.add_argument('--cc',default='clang')
    parser.add_argument('--cc-arg',action='append',default=[],help='extra compiler driver argument')
    parser.add_argument('--ar',help='static archive tool, otherwise discovered next to compiler or on PATH')
    parser.add_argument('--platform',choices=('windows','linux'),default='windows' if os.name=='nt' else 'linux')
    parser.add_argument('--target',help='optional Clang cross target')
    parser.add_argument('--output',type=Path,default=ROOT/'build')
    args=parser.parse_args()
    if not args.target and platform.machine().lower() not in ('amd64','x86_64'):
        parser.error('native execution requires x86-64')
    windows=args.platform=='windows'
    output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    objects=[]
    for source in sorted((ROOT/'asm').glob('*.asm')):
        obj=output/(source.stem+('.obj' if windows else '.o'))
        subprocess.run([args.nasm,'-f','win64' if windows else 'elf64','-w+error','-I',str(ROOT/'asm')+os.sep,'-o',obj,source],check=True)
        objects.append(obj)
    compiler=[args.cc,*args.cc_arg]+(['--target='+args.target] if args.target else [])
    flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'include')]
    link=['-Wl,--no-insert-timestamp','-static-libgcc'] if windows else ['-Wl,--build-id=none']
    shared=output/('byteforge.dll' if windows else 'libbyteforge.so')
    subprocess.run([*compiler,'-shared',*objects,*link,'-Wl,--export-all-symbols' if windows else '-Wl,-z,noexecstack','-o',shared],check=True)
    sibling=Path(args.cc).resolve().with_name('llvm-ar.exe' if os.name=='nt' else 'llvm-ar')
    archive_tool=args.ar or (str(sibling) if sibling.is_file() else (shutil.which('llvm-ar') or shutil.which('ar')))
    if not archive_tool: parser.error('a static archive tool is required')
    subprocess.run([archive_tool,'rcsD',output/'libbyteforge.a',*objects],check=True)
    cli=ROOT/'src/main.c'
    if cli.exists():
        subprocess.run([*compiler,*flags,cli,*objects,*link,'-o',output/('byteforge.exe' if windows else 'byteforge')],check=True)
    print(shared)
if __name__=='__main__': main()
