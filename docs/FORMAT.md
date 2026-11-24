# ByteForge bytecode and API

All encoded integers are little-endian. The guest data read by `u16be`, `u32be` and `u64be` is big-endian.

## Format v1

The 16-byte header has four-byte magic `BFG1`, a two-byte version (`1`), two zero flag bytes, a four-byte instruction count and four zero reserved bytes. Exact size is `16 + count * 16`, with `1 <= count <= 1024`. Trailing bytes are rejected.

Every 16-byte instruction has one opcode byte, seven zero reserved bytes and an eight-byte immediate. Unused immediates must be zero. The operand stack contains unsigned 64-bit values.

| Opcode | Name | Stack behavior | Immediate |
| --- | --- | --- | --- |
| 1 | const | push value | Any uint64 |
| 2 | len | push captured length | Zero |
| 3–6 | u8/u16be/u32be/u64be | push loaded value | Literal byte offset |
| 7–9 | and/or/xor | pop b, pop a, push a op b | Zero |
| 10–11 | shl/shr | pop count, pop value, push result | Zero |
| 12–13 | add/sub | pop b, pop a, push modular result | Zero |
| 14–19 | eq/ne/lt/le/gt/ge | pop b, pop a, push unsigned comparison | Zero |
| 20 | not | replace top with logical NOT | Zero |
| 21 | jump | preserve stack, jump | Absolute instruction index |
| 22 | jz | pop condition, jump if zero | Absolute instruction index |
| 23 | ret | require exactly one value and return it | Zero |
| 24 | invert | replace top with bitwise inversion | Zero |

A branch target must be greater than the current index and smaller than the instruction count. `ret` must be the final instruction. Every instruction must be statically reachable, and every predecessor of a join must supply the same stack depth. Falling off the program, underflow, overflow and hidden unreachable instructions are rejected. All arithmetic wraps modulo 2^64. A shift by 64 or more returns zero.

The verifier propagates one byte of abstract stack depth per instruction through the forward control-flow graph. No fixed-point loop is needed because all edges move forward. Execution separately validates stack operations, branch targets, read bounds and instruction fuel. Loads check `offset <= size` and `width <= size - offset` before dereferencing, avoiding offset-addition overflow.

Opcode 25, `u16le`, pushes a little-endian 16-bit value at its literal offset. Its stack and bounds rules match the other loads. Older engines reject this newly supported opcode.

Opcode 26, `u32le`, pushes a little-endian 32-bit value at its literal offset. Its stack and bounds rules match the other loads. Older engines reject this newly supported opcode.

Opcode 27, `u64le`, pushes a little-endian 64-bit value at its literal offset. Its stack and bounds rules match the other loads. Older engines reject this newly supported opcode.

Opcode 28, `mul`, pops b and a and pushes their modular multiplication. Its immediate is zero.

Opcode 29, `udiv`, pops b and a and pushes their unsigned division. Its immediate is zero.

Opcode 30, `umod`, pops b and a and pushes their unsigned remainder. Its immediate is zero.

## C API

`include/byteforge.h` defines the public functions. The core's four exported functions are `bf_version`, `bf_compile`, `bf_verify` and `bf_eval`.

```c
unsigned char program[BF_MAX_PROGRAM];
bf_compile_info compiled;
const char rule[] = "len >= 4 && u32be(0) == 0x7f454c46";
int status = bf_compile(rule, sizeof(rule)-1, program, sizeof(program), &compiled);
if (status == BF_OK) {
    uint64_t value = 0;
    status = bf_eval(program, compiled.size, input, input_size, &value);
}
```

`bf_compile` requires an output-info structure. It returns a byte count only on success. Ignore output bytes after any compiler error. Source offsets identify the token at which compilation failed. It checks output capacity before emission and re-verifies the completed program before success.

`bf_verify` accepts an optional info pointer. Its info reports maximum stack depth on success or an instruction index on body errors. `UINT32_MAX` identifies a header error. The output depth is zero on failure.

`bf_eval` requires a valid uint64 output pointer and resets it to zero before verification. A null input pointer is accepted only when input size is zero. Each evaluation re-verifies the program. Hold program and input bytes immutable throughout the call; this interface does not cache caller-owned memory or defend against a malicious embedding process.

Status values are 0 (`BF_OK`), 1 (`BF_BAD_PROGRAM`), 2 (`BF_SHORT_INPUT`), 3 (`BF_SYNTAX`), 4 (`BF_CAPACITY`) 5 (`BF_ARGUMENT`) and 6 (`BF_ARITHMETIC`). A zero divisor returns `BF_ARITHMETIC` with the output value zero; it never invokes a hardware divide by zero. Guest return values are separate from status. Any nonzero return value is a match in the CLI.

## Native boundaries

The NASM code supports Microsoft x64 and System V x86-64 integer calling conventions. Public and framed parser functions preserve nonvolatile registers, reserve Windows shadow space and align nested calls. Framed Windows functions have `.pdata`/`.xdata` unwind records. Leaf helpers occupy separate ranges. Test probes seed preserved registers around the three principal APIs and run reads immediately before inaccessible pages.

The engine does not allocate executable pages, invoke native bytes from the program, call guest-provided functions or perform I/O. The C adapter performs explicit file I/O. This is an in-process bytecode boundary, not isolation from invalid host pointers, concurrent buffer mutation or a compromised process.

ABI references: [Microsoft x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention) and [x86-64 System V ABI project](https://gitlab.com/x86-psABIs/x86-64-ABI). Assembly syntax is documented by [NASM](https://www.nasm.us/docs.php).
