"""Assemble ByteForge's native core and link the optional C file interface."""
from argparse import ArgumentParser
import os
from pathlib import Path
import platform
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--nasm',default='nasm')
    parser.add_argument('--cc',default='clang')
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
    compiler=[args.cc]+(['--target='+args.target] if args.target else [])
    flags=['-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'include')]
    shared=output/('byteforge.dll' if windows else 'libbyteforge.so')
    subprocess.run([*compiler,'-shared',*objects,'-Wl,--export-all-symbols' if windows else '-Wl,-z,noexecstack','-o',shared],check=True)
    cli=ROOT/'src/main.c'
    if cli.exists():
        subprocess.run([*compiler,*flags,cli,*objects,'-o',output/('byteforge.exe' if windows else 'byteforge')],check=True)
    print(shared)
if __name__=='__main__': main()
