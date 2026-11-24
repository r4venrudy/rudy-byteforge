; Reentrant source compiler. All scanner and emitter state is caller-local.
bits 64
default rel
%include "abi.inc"
%include "opcodes.inc"
extern bf_verify
%define C_SRC 0
%define C_LEN 8
%define C_POS 16
%define C_OUT 24
%define C_CAP 32
%define C_COUNT 40
%define C_TOKEN 44
%define C_DEPTH 48
%define C_ERROR 52
%define C_VALUE 56
%define C_ERRPOS 64
%define C_START 80
%define C_AUX 88
%define T_NUM 256
%define T_LEN 257
%define T_U8 260
%define T_U16 261
%define T_U32 262
%define T_U64 263
%define T_EQ 264
%define T_NE 265
%define T_LE 266
%define T_GE 267
%define T_SHL 268
%define T_SHR 269
%define T_AND 270
%define T_OR 271
%define T_U64LE 274
%define T_U32LE 273
%define T_U16LE 272
section .text
BF_ENTER bf_compile,168
 mov r12,A1
 mov r13,A2
 mov r14,A3
 mov r15,A4
%if WINDOWS
 mov rbx,[rsp+168+104]
%else
 mov rbx,r8
%endif
 test rbx,rbx
 jz .argument
 mov qword [rbx],0
 mov qword [rbx+8],0
 test r12,r12
 jz .argument
 cmp r13,BF_MAX_SOURCE
 ja .syntax_direct
 test r14,r14
 jz .capacity_direct
 cmp r15,16
 jb .capacity_direct
 mov qword [r14],0
 mov qword [r14+8],0
 lea rbp,[rsp+32]
 mov [rbp+C_SRC],r12
 mov [rbp+C_LEN],r13
 mov qword [rbp+C_POS],0
 mov [rbp+C_OUT],r14
 mov [rbp+C_CAP],r15
 mov qword [rbp+C_COUNT],0
 mov qword [rbp+C_DEPTH],0
 mov qword [rbp+C_VALUE],0
 mov qword [rbp+C_ERRPOS],0
 mov qword [rbp+C_START],0
 call bf_lex
 cmp dword [rbp+C_ERROR],0
 jne .failure
 mov ecx,1
 call bf_expr
 cmp dword [rbp+C_ERROR],0
 jne .failure
 cmp dword [rbp+C_TOKEN],0
 jne .syntax
.finish_expression:
 mov ecx,BF_RET
 xor eax,eax
 call bf_emit
 cmp dword [rbp+C_ERROR],0
 jne .failure
 mov dword [r14],0x31474642
 mov dword [r14+4],1
 mov eax,[rbp+C_COUNT]
 mov [r14+8],eax
 mov dword [r14+12],0
 shl rax,4
 add rax,16
 mov r13,rax
 mov A1,r14
 mov A2,r13
 xor A3,A3
 BF_EXTERN_CALL bf_verify
 test eax,eax
 jnz .internal_failure
 mov [rbx],r13
 xor eax,eax
 jmp .done
.internal_failure:
 mov qword [r14],0
 mov dword [rbp+C_ERROR],1
 jmp .failure
.syntax:
 mov eax,3
 call bf_error
.failure:
 mov eax,[rbp+C_ERRPOS]
 mov [rbx+8],eax
 mov eax,[rbp+C_ERROR]
 jmp .done
.syntax_direct:
 mov eax,3
 jmp .done
.capacity_direct:
 mov eax,4
 jmp .done
.argument:
 mov eax,5
.done:
BF_LEAVE bf_compile,168

; ECX opcode, RAX immediate. Capacity is checked before either store.
bf_emit:
 cmp dword [rbp+C_ERROR],0
 jne .return
 mov r10d,[rbp+C_COUNT]
 cmp r10d,BF_MAX_INSTRUCTIONS
 jae .capacity
 lea r9d,[r10+2]
 shl r9,4
 cmp r9,[rbp+C_CAP]
 ja .capacity
 mov r8,r10
 shl r8,4
 add r8,[rbp+C_OUT]
 mov qword [r8+16],0
 mov [r8+16],cl
 mov [r8+24],rax
 inc dword [rbp+C_COUNT]
.return:
 ret
.capacity:
 mov eax,4
 jmp bf_error

bf_error:
 cmp dword [rbp+C_ERROR],0
 jne .return
 mov [rbp+C_ERROR],eax
 mov eax,[rbp+C_START]
 mov [rbp+C_ERRPOS],eax
.return:
 ret

bf_lex:
 cmp dword [rbp+C_ERROR],0
 jne .return
 mov r8,[rbp+C_SRC]
 mov r9,[rbp+C_POS]
 mov r11,[rbp+C_LEN]
.space:
 cmp r9,r11
 jae .eof
 movzx eax,byte [r8+r9]
 cmp al,' '
 je .skip
 cmp al,9
 je .skip
 cmp al,10
 je .skip
 cmp al,13
 jne .start
.skip:
 inc r9
 jmp .space
.start:
 mov [rbp+C_START],r9
 cmp al,'0'
 jb .punctuation
 cmp al,'9'
 jbe .number
 cmp al,'a'
 jb .punctuation
 cmp al,'z'
 jbe .identifier
 jmp .punctuation
.number:
 mov r10d,10
 cmp al,'0'
 jne .digits_start
 lea rdx,[r9+1]
 cmp rdx,r11
 jae .digits_start
 movzx ecx,byte [r8+rdx]
 or ecx,32
 cmp ecx,'x'
 jne .digits_start
 add r9,2
 mov r10d,16
.digits_start:
 mov [rbp+C_AUX],r9
 xor eax,eax
.digit:
 cmp r9,r11
 jae .digits_end
 movzx ecx,byte [r8+r9]
 cmp ecx,'0'
 jb .digits_end
 cmp ecx,'9'
 jbe .decimal
 cmp r10d,16
 jne .digits_end
 or ecx,32
 cmp ecx,'a'
 jb .digits_end
 cmp ecx,'f'
 ja .digits_end
 sub ecx,'a'-10
 jmp .accumulate
.decimal:
 sub ecx,'0'
.accumulate:
 mul r10
 test rdx,rdx
 jnz .bad
 add rax,rcx
 jc .bad
 inc r9
 jmp .digit
.digits_end:
 cmp r9,[rbp+C_AUX]
 je .bad
 mov [rbp+C_VALUE],rax
 mov eax,T_NUM
 jmp .token
.identifier:
 inc r9
.identifier_loop:
 cmp r9,r11
 jae .identifier_end
 movzx ecx,byte [r8+r9]
 cmp ecx,'0'
 jb .identifier_end
 cmp ecx,'9'
 jbe .identifier_next
 cmp ecx,'a'
 jb .identifier_end
 cmp ecx,'z'
 ja .identifier_end
.identifier_next:
 inc r9
 jmp .identifier_loop
.identifier_end:
 mov rdx,[rbp+C_START]
 mov rcx,r9
 sub rcx,rdx
 cmp ecx,2
 je .id_u8
 cmp ecx,3
 je .id_len
 cmp ecx,5
 jne .bad
 cmp byte [r8+rdx+4],'e'
 jne .bad
 cmp dword [r8+rdx],'u16l'
 je .id_u16le
 cmp dword [r8+rdx],'u32l'
 je .id_u32le
 cmp dword [r8+rdx],'u64l'
 je .id_u64le
 cmp dword [r8+rdx],'u16b'
 je .id_u16
 cmp dword [r8+rdx],'u32b'
 je .id_u32
 cmp dword [r8+rdx],'u64b'
 jne .bad
 mov eax,T_U64
 jmp .token
.id_u16: mov eax,T_U16
 jmp .token
.id_u32: mov eax,T_U32
 jmp .token
.id_u16le: mov eax,T_U16LE
 jmp .token
.id_u32le: mov eax,T_U32LE
 jmp .token
.id_u64le: mov eax,T_U64LE
 jmp .token
.id_u8:
 cmp word [r8+rdx],'u8'
 jne .bad
 mov eax,T_U8
 jmp .token
.id_len:
 cmp word [r8+rdx],'le'
 jne .bad
 cmp byte [r8+rdx+2],'n'
 jne .bad
 mov eax,T_LEN
 jmp .token
.punctuation:
 inc r9
 xor edx,edx
 cmp r9,r11
 jae .operator
 movzx edx,byte [r8+r9]
.operator:
 cmp al,'='
 je .equal
 cmp al,'!'
 je .not
 cmp al,'<'
 je .less
 cmp al,'>'
 je .greater
 cmp al,'&'
 je .and
 cmp al,'|'
 je .or
 cmp al,'('
 je .token
 cmp al,')'
 je .token
 cmp al,'+'
 je .token
 cmp al,'-'
 je .token
 cmp al,'^'
 je .token
 cmp al,'*'
 je .token
 cmp al,'/'
 je .token
 cmp al,'~'
 je .token
 jmp .bad
.equal:
 cmp dl,'='
 jne .bad
 mov eax,T_EQ
 jmp .double
.not:
 cmp dl,'='
 jne .token
 mov eax,T_NE
 jmp .double
.less:
 cmp dl,'='
 je .le
 cmp dl,'<'
 jne .token
 mov eax,T_SHL
 jmp .double
.le: mov eax,T_LE
 jmp .double
.greater:
 cmp dl,'='
 je .ge
 cmp dl,'>'
 jne .token
 mov eax,T_SHR
 jmp .double
.ge: mov eax,T_GE
 jmp .double
.and:
 cmp dl,'&'
 jne .token
 mov eax,T_AND
 jmp .double
.or:
 cmp dl,'|'
 jne .token
 mov eax,T_OR
.double:
 inc r9
.token:
 mov [rbp+C_TOKEN],eax
 mov [rbp+C_POS],r9
.return:
 ret
.eof:
 mov [rbp+C_START],r9
 xor eax,eax
 jmp .token
.bad:
 mov eax,3
 jmp bf_error

; Precedence climbing. Private functions share the caller-local RBP context.
BF_ENTER bf_expr,72,0
 mov r12d,ecx
 inc dword [rbp+C_DEPTH]
 cmp dword [rbp+C_DEPTH],64
 ja .syntax
 call bf_unary
.loop:
 cmp dword [rbp+C_ERROR],0
 jne .done
 mov eax,[rbp+C_TOKEN]
 call bf_binary
 cmp ecx,r12d
 jb .done
 mov r13d,edx
 mov r14d,ecx
 cmp r13d,100
 jae .logical
 call bf_lex
 lea ecx,[r14+1]
 call bf_expr
 cmp dword [rbp+C_ERROR],0
 jne .done
 mov ecx,r13d
 xor eax,eax
 call bf_emit
 jmp .loop
.logical:
 mov [rsp+32],r14d ; RHS precedence survives recursive calls
 mov r14d,[rbp+C_COUNT]
 mov ecx,BF_JZ
 xor eax,eax
 call bf_emit
 cmp r13d,100
 je .logical_and
 ; OR: a true left value yields 1 and skips the entire right side.
 mov ecx,BF_CONST
 mov eax,1
 call bf_emit
 mov r15d,[rbp+C_COUNT]
 mov ecx,BF_JUMP
 xor eax,eax
 call bf_emit
 mov eax,[rbp+C_COUNT]
 mov ecx,r14d
 call bf_patch
 call bf_lex
 mov ecx,[rsp+32]
 inc ecx
 call bf_expr
 call bf_boolean
 mov eax,[rbp+C_COUNT]
 mov ecx,r15d
 call bf_patch
 jmp .loop
.logical_and:
 ; AND: a false left value skips the right side and supplies zero.
 call bf_lex
 mov ecx,[rsp+32]
 inc ecx
 call bf_expr
 call bf_boolean
 mov r15d,[rbp+C_COUNT]
 mov ecx,BF_JUMP
 xor eax,eax
 call bf_emit
 mov eax,[rbp+C_COUNT]
 mov ecx,r14d
 call bf_patch
 mov ecx,BF_CONST
 xor eax,eax
 call bf_emit
 mov eax,[rbp+C_COUNT]
 mov ecx,r15d
 call bf_patch
 jmp .loop
.syntax:
 mov eax,3
 call bf_error
.done:
 dec dword [rbp+C_DEPTH]
 mov eax,[rbp+C_ERROR]
BF_LEAVE bf_expr,72

BF_ENTER bf_unary,40,0
 inc dword [rbp+C_DEPTH]
 cmp dword [rbp+C_DEPTH],64
 ja .syntax
 mov r12d,[rbp+C_TOKEN]
 cmp r12d,T_NUM
 je .number
 cmp r12d,T_LEN
 je .length
 cmp r12d,T_U8
 jb .not_load
 cmp r12d,T_U64
 jbe .load
.not_load:
 cmp r12d,T_U64LE
 je .load_u64le
 cmp r12d,T_U32LE
 je .load_u32le
 cmp r12d,T_U16LE
 je .load_u16le
 cmp r12d,'('
 je .parenthesis
 cmp r12d,'!'
 je .prefix
 cmp r12d,'~'
 je .prefix
 cmp r12d,'-'
 je .negative
 cmp r12d,'+'
 je .prefix
 jmp .syntax
.negative:
 mov ecx,BF_CONST
 xor eax,eax
 call bf_emit
.prefix:
 call bf_lex
 call bf_unary
 cmp dword [rbp+C_ERROR],0
 jne .done
 cmp r12d,'+'
 je .done
 mov ecx,BF_NOT
 cmp r12d,'!'
 je .emit_unary
 mov ecx,BF_INVERT
 cmp r12d,'~'
 je .emit_unary
 mov ecx,BF_SUB
.emit_unary:
 xor eax,eax
 call bf_emit
 jmp .done
.number:
 mov rax,[rbp+C_VALUE]
 mov ecx,BF_CONST
 call bf_emit
 call bf_lex
 jmp .done
.length:
 mov ecx,BF_LEN
 xor eax,eax
 call bf_emit
 call bf_lex
 jmp .done
.load_u16le:
 mov r12d,BF_U16LE
 jmp .load_arguments
.load_u32le:
 mov r12d,BF_U32LE
 jmp .load_arguments
.load_u64le:
 mov r12d,BF_U64LE
 jmp .load_arguments
.load:
 sub r12d,257
.load_arguments:
 call bf_lex
 cmp dword [rbp+C_TOKEN],'('
 jne .syntax
 call bf_lex
 cmp dword [rbp+C_TOKEN],T_NUM
 jne .syntax
 mov r13,[rbp+C_VALUE]
 call bf_lex
 cmp dword [rbp+C_TOKEN],')'
 jne .syntax
 call bf_lex
 mov ecx,r12d
 mov rax,r13
 call bf_emit
 jmp .done
.parenthesis:
 call bf_lex
 mov ecx,1
 call bf_expr
 cmp dword [rbp+C_TOKEN],')'
 jne .syntax
 call bf_lex
 jmp .done
.syntax:
 mov eax,3
 call bf_error
.done:
 dec dword [rbp+C_DEPTH]
 mov eax,[rbp+C_ERROR]
BF_LEAVE bf_unary,40

; Return precedence in ECX and opcode in EDX, or precedence zero.
bf_binary:
 xor ecx,ecx
 xor edx,edx
 cmp eax,'/'
 je .bf_udiv
 cmp eax,'*'
 je .bf_mul
 cmp eax,T_OR
 je .logical_or
 cmp eax,T_AND
 je .logical_and
 cmp eax,'|'
 je .or
 cmp eax,'^'
 je .xor
 cmp eax,'&'
 je .and
 cmp eax,T_EQ
 je .eq
 cmp eax,T_NE
 je .ne
 cmp eax,'<'
 je .lt
 cmp eax,T_LE
 je .le
 cmp eax,'>'
 je .gt
 cmp eax,T_GE
 je .ge
 cmp eax,T_SHL
 je .shl
 cmp eax,T_SHR
 je .shr
 cmp eax,'+'
 je .add
 cmp eax,'-'
 je .sub
 ret
.or: mov ecx,3
 mov edx,BF_OR
 ret
.xor: mov ecx,4
 mov edx,BF_XOR
 ret
.and: mov ecx,5
 mov edx,BF_AND
 ret
.eq: mov ecx,6
 mov edx,BF_EQ
 ret
.ne: mov ecx,6
 mov edx,BF_NE
 ret
.lt: mov ecx,7
 mov edx,BF_LT
 ret
.le: mov ecx,7
 mov edx,BF_LE
 ret
.gt: mov ecx,7
 mov edx,BF_GT
 ret
.ge: mov ecx,7
 mov edx,BF_GE
 ret
.shl: mov ecx,8
 mov edx,BF_SHL
 ret
.shr: mov ecx,8
 mov edx,BF_SHR
 ret
.add: mov ecx,9
 mov edx,BF_ADD
 ret
.sub: mov ecx,9
 mov edx,BF_SUB
 ret
.logical_or: mov ecx,1
 mov edx,101
 ret
.logical_and: mov ecx,2
 mov edx,100
 ret

.bf_mul: mov ecx,10
 mov edx,BF_MUL
 ret

.bf_udiv: mov ecx,10
 mov edx,BF_UDIV
 ret

; Internal helpers use only volatile registers and the immutable context base.
BF_ENTER bf_boolean,40,0
 mov ecx,BF_NOT
 xor eax,eax
 call bf_emit
 mov ecx,BF_NOT
 xor eax,eax
 call bf_emit
BF_LEAVE bf_boolean,40
bf_patch:
 cmp dword [rbp+C_ERROR],0
 jne .done
 cmp ecx,[rbp+C_COUNT]
 jae .bad
 mov r8,rcx
 shl r8,4
 add r8,[rbp+C_OUT]
 mov [r8+24],rax
.done: ret
.bad:
 mov eax,3
 jmp bf_error
BF_NOEXEC_STACK
