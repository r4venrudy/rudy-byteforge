#ifndef BYTEFORGE_H
#define BYTEFORGE_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { BF_OK=0, BF_BAD_PROGRAM=1, BF_SHORT_INPUT=2, BF_SYNTAX=3, BF_CAPACITY=4, BF_ARGUMENT=5, BF_ARITHMETIC=6 };
enum { BF_CONST=1, BF_LEN, BF_U8, BF_U16BE, BF_U32BE, BF_U64BE,
       BF_AND, BF_OR, BF_XOR, BF_SHL, BF_SHR, BF_ADD, BF_SUB,
       BF_EQ, BF_NE, BF_LT, BF_LE, BF_GT, BF_GE, BF_NOT,
       BF_JUMP, BF_JZ, BF_RET, BF_INVERT, BF_U16LE=25, BF_U32LE=26, BF_U64LE=27, BF_MUL=28, BF_UDIV=29 };
enum { BF_MAX_INSTRUCTIONS=1024, BF_MAX_STACK=64, BF_HEADER=16, BF_INSTRUCTION=16,
       BF_MAX_PROGRAM=BF_HEADER+BF_MAX_INSTRUCTIONS*BF_INSTRUCTION, BF_MAX_SOURCE=8192 };
typedef struct { uint32_t max_stack, error_pc; } bf_verify_info;
typedef struct { size_t size; uint32_t error_offset, reserved; } bf_compile_info;
uint32_t bf_version(void);
int bf_verify(const void *program, size_t size, bf_verify_info *info);
int bf_eval(const void *program, size_t program_size, const void *input, size_t input_size, uint64_t *result);
int bf_compile(const char *source, size_t source_size, void *output, size_t capacity, bf_compile_info *info);
#ifdef __cplusplus
}
#endif
#endif
