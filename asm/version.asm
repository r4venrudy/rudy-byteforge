bits 64
default rel
%include "abi.inc"
section .text
global bf_version
bf_version:
 mov eax,0x00010000
 ret
BF_NOEXEC_STACK
