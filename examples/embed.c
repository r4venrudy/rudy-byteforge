/* A standalone consumer linked to libbyteforge.a, with no test harness. */
#include "byteforge.h"
#include <stdio.h>
int main(void) {
    const char rule[]="len >= 4 && u32be(0) == 0x7f454c46";
    const unsigned char input[]={0x7f,'E','L','F'};
    unsigned char program[BF_MAX_PROGRAM];bf_compile_info compiled;
    if(bf_compile(rule,sizeof(rule)-1,program,sizeof program,&compiled)!=BF_OK) return 1;
    uint64_t value=0;
    if(bf_eval(program,compiled.size,input,sizeof input,&value)!=BF_OK||value!=1) return 1;
    puts("Standalone static-library consumer matched ELF magic");
    return 0;
}
