/* File/console interface only. Compiler, verifier and VM live in asm/. */
#include "byteforge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#define MAX_INPUT (16u*1024u*1024u)
#define MAX_CAPTURE (256u*1024u*1024u)
static unsigned char *read_file(const char *path,size_t limit,size_t *size) {
    FILE *file=fopen(path,"rb");
    if(!file) return NULL;
    unsigned char *data=malloc(limit+1);
    if(!data) { fclose(file);return NULL; }
    size_t count=fread(data,1,limit+1,file);
    int bad=ferror(file)||count>limit;
    if(fclose(file)) bad=1;
    if(bad) { free(data);return NULL; }
    *size=count;return data;
}
static uint32_t word32(const unsigned char *p,int big) {
    if(big) return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
    return ((uint32_t)p[3]<<24)|((uint32_t)p[2]<<16)|((uint32_t)p[1]<<8)|p[0];
}
static uint64_t word64(const unsigned char *p) {
    return word32(p,0)|((uint64_t)word32(p+4,0)<<32);
}
static int error(const char *message) { fprintf(stderr,"byteforge: %s\n",message);return 2; }
static const char *names[]={"invalid","const","len","u8","u16be","u32be","u64be","and","or","xor","shl","shr","add","sub","eq","ne","lt","le","gt","ge","not","jump","jz","ret","invert","u16le","u32le","u64le","mul"};

static int scan(const unsigned char *program,size_t program_size,const char *path) {
    FILE *file=fopen(path,"rb");
    if(!file) return error("cannot open capture");
    unsigned char header[24];
    int result=2;unsigned char *packet=NULL;
    if(fread(header,1,24,file)!=24) goto invalid;
    int big,nano;
    uint32_t magic=word32(header,0);
    if(magic==0xa1b2c3d4) { big=0;nano=0; }
    else if(magic==0xd4c3b2a1) { big=1;nano=0; }
    else if(magic==0xa1b23c4d) { big=0;nano=1; }
    else if(magic==0x4d3cb2a1) { big=1;nano=1; }
    else goto invalid;
    uint32_t version=word32(header+4,big);
    if(version!=(big?0x00020004u:0x00040002u)) goto invalid;
    uint32_t snap=word32(header+16,big),link=word32(header+20,big);
    if(!snap||snap>MAX_INPUT) goto invalid;
    packet=malloc(snap);
    if(!packet) goto invalid;
    uint64_t consumed=24,packets=0,matches=0,shorts=0;
    uint32_t indices[1024];size_t reported=0;
    for(;;) {
        unsigned char record[16];size_t got=fread(record,1,16,file);
        if(!got) { if(ferror(file)) goto invalid;break; }
        if(got!=16||packets>=1000000u) goto invalid;
        uint32_t fraction=word32(record+4,big),captured=word32(record+8,big),original=word32(record+12,big);
        if(fraction>=(nano?1000000000u:1000000u)||captured>snap||captured>original) goto invalid;
        consumed+=16u+(uint64_t)captured;
        if(consumed>MAX_CAPTURE||fread(packet,1,captured,file)!=captured) goto invalid;
        uint64_t value=0;int status=bf_eval(program,program_size,packet,captured,&value);
        if(status==BF_SHORT_INPUT) shorts++;
        else if(status!=BF_OK) goto invalid;
        else if(value) { matches++;if(reported<1024) indices[reported++]=(uint32_t)packets; }
        packets++;
    }
    printf("{\"schema\":\"rudy.byteforge.scan/v1\",\"link_type\":%u,\"packets\":%" PRIu64 ",\"matches\":%" PRIu64 ",\"short_inputs\":%" PRIu64 ",\"indices\":[",link,packets,matches,shorts);
    for(size_t i=0;i<reported;i++) printf("%s%u",i?",":"",indices[i]);
    printf("],\"indices_truncated\":%s}\n",matches>reported?"true":"false");
    result=matches?0:1;
    goto done;
invalid:
    fprintf(stderr,"byteforge: invalid, unsupported or oversized classic PCAP input\n");
done:
    free(packet);if(fclose(file)) result=2;return result;
}

int main(int argc,char **argv) {
    if(argc==2&&!strcmp(argv[1],"--version")) { puts("byteforge 0.1.0-preview");return 0; }
    if(argc==2&&!strcmp(argv[1],"--help")) {
        puts("ByteForge / verified binary rules in x86-64 Assembly\ncompile source.bf output.bfg\nverify program.bfg\ndisasm program.bfg\nrun program.bfg input.bin\nscan program.bfg capture.pcap\nCompile refuses to overwrite an existing output. Run/scan exit 1 when no match.");return 0;
    }
    if(argc<3) return error("expected compile, verify, disasm, run or scan; see --help");
    if(!strcmp(argv[1],"compile")) {
        if(argc!=4) return error("compile requires source and a new output path");
        size_t size=0;unsigned char *source=read_file(argv[2],BF_MAX_SOURCE,&size);
        if(!source) return error("cannot read bounded source file");
        unsigned char output[BF_MAX_PROGRAM];bf_compile_info info;
        int status=bf_compile((const char *)source,size,output,sizeof output,&info);free(source);
        if(status) { fprintf(stderr,"byteforge: compiler status %d at byte %u\n",status,info.error_offset);return 2; }
        FILE *file=fopen(argv[3],"wbx");
        if(!file) return error("cannot create output; existing files are preserved");
        int bad=fwrite(output,1,info.size,file)!=info.size;
        if(fclose(file)) bad=1;
        if(bad) { remove(argv[3]);return error("cannot complete compiled output"); }
        printf("{\"schema\":\"rudy.byteforge.compile/v1\",\"bytes\":%zu,\"instructions\":%u}\n",info.size,word32(output+8,0));return 0;
    }
    int inspect=!strcmp(argv[1],"verify"),disasm=!strcmp(argv[1],"disasm"),run=!strcmp(argv[1],"run"),capture=!strcmp(argv[1],"scan");
    if(!(inspect||disasm||run||capture)||argc!=((run||capture)?4:3)) return error("invalid command arguments");
    size_t size=0;unsigned char *program=read_file(argv[2],BF_MAX_PROGRAM,&size);
    if(!program) return error("cannot read bounded bytecode file");
    bf_verify_info info;int status=bf_verify(program,size,&info);
    if(status) { fprintf(stderr,"byteforge: invalid bytecode at instruction %u\n",info.error_pc);free(program);return 2; }
    if(inspect) printf("{\"schema\":\"rudy.byteforge.verify/v1\",\"instructions\":%u,\"max_stack\":%u}\n",word32(program+8,0),info.max_stack);
    else if(disasm) {
        for(uint32_t i=0;i<word32(program+8,0);i++) printf("%04u  %-8s 0x%016" PRIx64 "\n",i,names[program[16+i*16]],word64(program+24+i*16));
    } else if(capture) { int result=scan(program,size,argv[3]);free(program);return result; }
    else {
        size_t input_size=0;unsigned char *input=read_file(argv[3],MAX_INPUT,&input_size);
        if(!input) { free(program);return error("cannot read bounded input file"); }
        uint64_t value=0;status=bf_eval(program,size,input,input_size,&value);free(input);
        if(status==BF_SHORT_INPUT) { free(program);fprintf(stderr,"byteforge: rule read beyond captured input\n");return 3; }
        if(status) { free(program);return error("execution rejected"); }
        printf("{\"schema\":\"rudy.byteforge.run/v1\",\"value\":%" PRIu64 ",\"match\":%s}\n",value,value?"true":"false");
        free(program);return value?0:1;
    }
    free(program);return ferror(stdout)?2:0;
}
