"""Run guard-page and ABI tests against the actual Assembly objects."""
from argparse import ArgumentParser
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
parser=ArgumentParser(description=__doc__)
parser.add_argument('--nasm',default='nasm');parser.add_argument('--cc',default='clang');args=parser.parse_args()
windows=os.name=='nt';build=ROOT/'build';suffix='.obj' if windows else '.o'
probe=build/('abi_probe'+suffix)
subprocess.run([args.nasm,'-f','win64' if windows else 'elf64','-I',str(ROOT/'asm')+os.sep,'-o',probe,ROOT/'tests/abi_probe.asm'],check=True)
executable=build/('guard.exe' if windows else 'guard')
objects=[build/(file.stem+suffix) for file in sorted((ROOT/'asm').glob('*.asm'))]
subprocess.run([args.cc,'-O2','-Wall','-Wextra','-Werror','-I',ROOT/'include',ROOT/'tests/guard.c',probe,*objects,'-o',executable],check=True)
subprocess.run([executable],check=True)
consumer=build/('embed.exe' if windows else 'embed')
subprocess.run([args.cc,'-O2','-Wall','-Wextra','-Werror','-I',ROOT/'include',ROOT/'examples/embed.c',build/'libbyteforge.a','-o',consumer],check=True)
subprocess.run([consumer],check=True)
