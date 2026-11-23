; Structural and stack verification. No heap allocation or external calls.
bits 64
default rel
%include "abi.inc"
%include "opcodes.inc"
section .text
BF_ENTER bf_verify,1080
 mov r12,A1
 mov r13,A2
 mov r14,A3
 test r14,r14
 jz .header
 mov dword [r14],0
 mov dword [r14+4],-1
.header:
 test r12,r12
 jz .bad_header
 cmp r13,16
 jb .bad_header
 cmp dword [r12],0x31474642 ; BFG1
 jne .bad_header
 cmp dword [r12+4],1 ; version 1, flags 0
 jne .bad_header
 cmp dword [r12+12],0
 jne .bad_header
 mov r15d,[r12+8]
 test r15d,r15d
 jz .bad_header
 cmp r15d,BF_MAX_INSTRUCTIONS
 ja .bad_header
 mov eax,r15d
 shl rax,4
 add rax,16
 cmp rax,r13
 jne .bad_header
 lea rbp,[r12+16]
 lea r12,[rsp+32] ; one byte of abstract stack state per instruction
 mov rdi,r12
 mov ecx,BF_MAX_INSTRUCTIONS
 mov eax,255
 rep stosb
 mov byte [r12],0
 xor ebx,ebx ; instruction index
 xor esi,esi ; incoming stack depth
 xor r13d,r13d ; maximum stack depth
.instruction:
 movzx esi,byte [r12+rbx]
 cmp esi,255
 je .bad_pc ; hidden/unreachable instructions are outside the format
 mov eax,ebx
 shl rax,4
 lea r10,[rbp+rax]
 mov rdx,[r10]
 shr rdx,8
 jnz .bad_pc
 movzx ecx,byte [r10]
 mov rax,[r10+8]
 cmp ecx,BF_CONST
 je .push
 cmp ecx,BF_U8
 jb .not_load
 cmp ecx,BF_U64BE
 jbe .push
.not_load:
 cmp ecx,BF_JUMP
 je .jump
 cmp ecx,BF_JZ
 je .conditional
 test rax,rax
 jnz .bad_pc
 cmp ecx,BF_LEN
 je .push
 cmp ecx,BF_AND
 jb .bad_pc
 cmp ecx,BF_GE
 jbe .binary
 cmp ecx,BF_NOT
 je .unary
 cmp ecx,BF_INVERT
 je .unary
 cmp ecx,BF_RET
 jne .bad_pc
 cmp esi,1
 jne .bad_pc
 lea eax,[rbx+1]
 cmp eax,r15d
 jne .bad_pc
 test r14,r14
 jz .success
 mov [r14],r13d
.success:
 xor eax,eax
 jmp .done
.binary:
 cmp esi,2
 jb .bad_pc
 dec esi
 jmp .next
.unary:
 test esi,esi
 jz .bad_pc
 jmp .next
.push:
 cmp esi,BF_MAX_STACK
 jae .bad_pc
 inc esi
 cmp esi,r13d
 cmova r13d,esi
.next:
 lea eax,[rbx+1]
 cmp eax,r15d
 jae .bad_pc
 mov edx,esi
 call .merge
 jc .bad_pc
.advance:
 inc ebx
 cmp ebx,r15d
 jb .instruction
 jmp .bad_pc
.conditional:
 test esi,esi
 jz .bad_pc
 dec esi
.jump:
 cmp rax,rbx
 jbe .bad_pc
 cmp rax,r15
 jae .bad_pc
 mov edx,esi
 call .merge
 jc .bad_pc
 cmp ecx,BF_JUMP
 je .advance
 jmp .next
.merge:
 mov r9b,[r12+rax]
 cmp r9b,255
 je .assign
 cmp r9b,dl
 jne .conflict
 clc
 ret
.assign:
 mov [r12+rax],dl
 clc
 ret
.conflict:
 stc
 ret
.bad_pc:
 test r14,r14
 jz .bad_header
 mov [r14+4],ebx
.bad_header:
 mov eax,1
.done:
BF_LEAVE bf_verify,1080
BF_NOEXEC_STACK
