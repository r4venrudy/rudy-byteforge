; Verified unsigned 64-bit execution. Program bytes are never native code.
bits 64
default rel
%include "abi.inc"
%include "opcodes.inc"
extern bf_verify
section .text
BF_ENTER bf_eval,568
 mov r12,A1
 mov r13,A2
 mov r14,A3
 mov rbx,A4
%if WINDOWS
 mov r15,[rsp+568+104]
%else
 mov r15,r8
%endif
 test r15,r15
 jz .argument
 mov qword [r15],0
 test r14,r14
 jnz .verify
 test rbx,rbx
 jnz .argument
.verify:
 mov A1,r12
 mov A2,r13
 xor A3,A3
 BF_EXTERN_CALL bf_verify
 test eax,eax
 jnz .done
 mov r13d,[r12+8]
 add r12,16
 lea rbp,[rsp+32]
 xor esi,esi ; operand stack depth
 xor edi,edi ; program counter
 mov qword [rsp+552],0 ; independent instruction fuel
.step:
 cmp rdi,r13
 jae .invalid
 inc qword [rsp+552]
 cmp [rsp+552],r13
 ja .invalid
 mov rax,rdi
 shl rax,4
 lea r10,[r12+rax]
 movzx ecx,byte [r10]
 mov r8,[r10+8]
 cmp ecx,BF_CONST
 je .constant
 cmp ecx,BF_LEN
 je .length
 cmp ecx,BF_U8
 jb .invalid
 cmp ecx,BF_U64BE
 jbe .load
 cmp ecx,BF_AND
 jb .invalid
 cmp ecx,BF_GE
 jbe .binary
 cmp ecx,BF_NOT
 je .unary
 cmp ecx,BF_INVERT
 je .unary
 cmp ecx,BF_RET
 jne .invalid
 cmp esi,1
 jne .invalid
 mov rax,[rbp]
 mov [r15],rax
 xor eax,eax
 jmp .done
.constant:
 mov rax,r8
 jmp .push
.length:
 mov rax,rbx
 jmp .push
.load:
 mov edx,1
 cmp ecx,BF_U8
 je .bounds
 mov edx,2
 cmp ecx,BF_U16BE
 je .bounds
 mov edx,4
 cmp ecx,BF_U32BE
 je .bounds
 mov edx,8
.bounds:
 cmp r8,rbx
 ja .short
 mov r9,rbx
 sub r9,r8 ; subtraction avoids offset+width overflow
 cmp r9,rdx
 jb .short
 lea rdx,[r14+r8]
 cmp ecx,BF_U8
 je .byte
 cmp ecx,BF_U16BE
 je .word
 cmp ecx,BF_U32BE
 je .dword
 mov rax,[rdx]
 bswap rax
 jmp .push
.byte:
 movzx eax,byte [rdx]
 jmp .push
.word:
 movzx eax,word [rdx]
 xchg al,ah
 jmp .push
.dword:
 mov eax,[rdx]
 bswap eax
.push:
 cmp esi,BF_MAX_STACK
 jae .invalid
 mov [rbp+rsi*8],rax
 inc esi
 jmp .next
.unary:
 test esi,esi
 jz .invalid
 mov rax,[rbp+rsi*8-8]
 cmp ecx,BF_NOT
 jne .invert
 test rax,rax
 sete al
 movzx eax,al
 jmp .replace
.invert:
 not rax
.replace:
 mov [rbp+rsi*8-8],rax
 jmp .next
.binary:
 cmp esi,2
 jb .invalid
 dec esi
 mov rdx,[rbp+rsi*8]
 mov rax,[rbp+rsi*8-8]
 cmp ecx,BF_AND
 je .and
 cmp ecx,BF_OR
 je .or
 cmp ecx,BF_XOR
 je .xor
 cmp ecx,BF_ADD
 je .add
 cmp ecx,BF_SUB
 je .sub
 cmp ecx,BF_SHL
 je .shl
 cmp ecx,BF_SHR
 je .shr
 cmp rax,rdx
 sete r8b
 setne r9b
 setb r10b
 setbe r11b
 seta al
 setae dl
 cmp ecx,BF_EQ
 je .eq
 cmp ecx,BF_NE
 je .ne
 cmp ecx,BF_LT
 je .lt
 cmp ecx,BF_LE
 je .le
 cmp ecx,BF_GT
 je .gt
 movzx eax,dl
 jmp .replace
.eq: movzx eax,r8b
 jmp .replace
.ne: movzx eax,r9b
 jmp .replace
.lt: movzx eax,r10b
 jmp .replace
.le: movzx eax,r11b
 jmp .replace
.gt: movzx eax,al
 jmp .replace
.and: and rax,rdx
 jmp .replace
.or: or rax,rdx
 jmp .replace
.xor: xor rax,rdx
 jmp .replace
.add: add rax,rdx
 jmp .replace
.sub: sub rax,rdx
 jmp .replace
.shl:
 mov rcx,rdx
 xor edx,edx
 cmp rcx,64
 cmovae rax,rdx
 shl rax,cl
 jmp .replace
.shr:
 mov rcx,rdx
 xor edx,edx
 cmp rcx,64
 cmovae rax,rdx
 shr rax,cl
 jmp .replace
.next:
 inc edi
 jmp .step
.argument:
 mov eax,5
 jmp .done
.short:
 mov eax,2
 jmp .done
.invalid:
 mov eax,1
.done:
BF_LEAVE bf_eval,568
BF_NOEXEC_STACK
