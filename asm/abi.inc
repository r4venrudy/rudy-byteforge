; Shared Microsoft x64 / System V integer ABI, NASM 2.16+.
%ifidn __OUTPUT_FORMAT__,win64
 %define A1 rcx
 %define A2 rdx
 %define A3 r8
 %define A4 r9
 %define WINDOWS 1
%else
 %define A1 rdi
 %define A2 rsi
 %define A3 rdx
 %define A4 rcx
 %define WINDOWS 0
%endif

; Eight preserved registers and an 8-mod-16 frame align nested calls.
; Frames include 32 bytes of Windows shadow space and stay below one page.
%macro BF_ENTER 2
global %1
%1:
 push rbx
%1.p1:
 push rbp
%1.p2:
 push rsi
%1.p3:
 push rdi
%1.p4:
 push r12
%1.p5:
 push r13
%1.p6:
 push r14
%1.p7:
 push r15
%1.p8:
 sub rsp,%2
%1.prologue:
%endmacro

%macro BF_LEAVE 2
 add rsp,%2
 pop r15
 pop r14
 pop r13
 pop r12
 pop rdi
 pop rsi
 pop rbp
 pop rbx
 ret
%1.end:
%if WINDOWS
 section .pdata rdata align=4
 dd %1 wrt ..imagebase, %1.end wrt ..imagebase, %1.unwind wrt ..imagebase
 section .xdata rdata align=4
%1.unwind:
 db 1, %1.prologue-%1, 10, 0
 db %1.prologue-%1, 1
 dw %2/8
 db %1.p8-%1, 0xf0, %1.p7-%1, 0xe0
 db %1.p6-%1, 0xd0, %1.p5-%1, 0xc0
 db %1.p4-%1, 0x70, %1.p3-%1, 0x60
 db %1.p2-%1, 0x50, %1.p1-%1, 0x30
 section .text
%endif
%endmacro

%macro BF_EXTERN_CALL 1
%if WINDOWS
 call %1
%else
 call %1 wrt ..plt
%endif
%endmacro

%macro BF_NOEXEC_STACK 0
%ifidn __OUTPUT_FORMAT__,elf64
 section .note.GNU-stack noalloc noexec nowrite progbits
%endif
%endmacro
