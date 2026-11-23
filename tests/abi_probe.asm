bits 64
default rel
%include "abi.inc"
section .text
; Probe a public five-argument API while checking the platform's saved GPRs.
BF_ENTER bf_abi_probe,120
 mov r10,A2
 mov r11,A1
 mov [rsp+72],r11
 mov rax,[r10]
 mov [rsp+32],rax
 mov rax,[r10+8]
 mov [rsp+40],rax
 mov rax,[r10+16]
 mov [rsp+48],rax
 mov rax,[r10+24]
 mov [rsp+56],rax
 mov rax,[r10+32]
 mov [rsp+64],rax
 mov rbx,0x1122334455667788
 mov rbp,0x2233445566778899
 mov r12,0x33445566778899aa
 mov r13,0x445566778899aabb
 mov r14,0x5566778899aabbcc
 mov r15,0x66778899aabbccdd
%if WINDOWS
 mov rsi,0x778899aabbccddee
 mov rdi,0x8899aabbccddeeff
%endif
 mov A1,[rsp+32]
 mov A2,[rsp+40]
 mov A3,[rsp+48]
 mov A4,[rsp+56]
%if WINDOWS
 mov rax,[rsp+64]
 mov [rsp+32],rax
%else
 mov r8,[rsp+64]
%endif
 call [rsp+72]
 mov rax,0x1122334455667788
 cmp rax,rbx
 jne .bad
 mov rax,0x2233445566778899
 cmp rax,rbp
 jne .bad
 mov rax,0x33445566778899aa
 cmp rax,r12
 jne .bad
 mov rax,0x445566778899aabb
 cmp rax,r13
 jne .bad
 mov rax,0x5566778899aabbcc
 cmp rax,r14
 jne .bad
 mov rax,0x66778899aabbccdd
 cmp rax,r15
 jne .bad
%if WINDOWS
 mov rax,0x778899aabbccddee
 cmp rax,rsi
 jne .bad
 mov rax,0x8899aabbccddeeff
 cmp rax,rdi
 jne .bad
%endif
 xor eax,eax
 jmp .done
.bad: mov eax,1
.done:
BF_LEAVE bf_abi_probe,120
BF_NOEXEC_STACK
