#include "byteforge.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif
extern int bf_abi_probe(void *,const uintptr_t *);
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"guard assertion line %d\n",__LINE__);return 1; } } while(0)
int main(void) {
    size_t page;
    unsigned char *memory;
#ifdef _WIN32
    SYSTEM_INFO system;GetSystemInfo(&system);page=system.dwPageSize;
    memory=VirtualAlloc(NULL,page*2,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    CHECK(memory);DWORD previous;CHECK(VirtualProtect(memory+page,page,PAGE_NOACCESS,&previous));
#else
    page=(size_t)sysconf(_SC_PAGESIZE);
    memory=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    CHECK(memory!=MAP_FAILED);CHECK(!mprotect(memory+page,page,PROT_NONE));
#endif
    unsigned char program[BF_MAX_PROGRAM];bf_compile_info compiled;bf_verify_info verified;
    const char *text="u64be(0)";
    CHECK(bf_compile(text,strlen(text),program,sizeof program,&compiled)==0);
    memset(memory+page-8,1,8);uint64_t value=0;
    CHECK(bf_eval(program,compiled.size,memory+page-8,8,&value)==0);
    CHECK(value==UINT64_C(0x0101010101010101));
    CHECK(bf_eval(program,compiled.size,memory+page-7,7,&value)==BF_SHORT_INPUT&&value==0);
    CHECK(bf_verify(memory+page-15,15,&verified)==BF_BAD_PROGRAM);
    memcpy(memory+page-3,"len",3);
    CHECK(bf_compile((const char *)memory+page-3,3,program,sizeof program,&compiled)==0);
    uintptr_t args[5]={(uintptr_t)program,compiled.size,(uintptr_t)&verified,0,0};
    CHECK(!bf_abi_probe((void *)(uintptr_t)bf_verify,args));
    args[2]=(uintptr_t)(memory+page-8);args[3]=8;args[4]=(uintptr_t)&value;
    CHECK(!bf_abi_probe((void *)(uintptr_t)bf_eval,args));
    CHECK(value==8);
    args[0]=(uintptr_t)"1 || u8(999)";args[1]=strlen((const char *)args[0]);
    args[2]=(uintptr_t)program;args[3]=sizeof program;args[4]=(uintptr_t)&compiled;
    CHECK(!bf_abi_probe((void *)(uintptr_t)bf_compile,args));
    CHECK(compiled.size>16);
#ifdef _WIN32
    CHECK(VirtualFree(memory,0,MEM_RELEASE));
#else
    CHECK(!munmap(memory,page*2));
#endif
    puts("Guard-page reads and three public ABI register probes passed");return 0;
}
