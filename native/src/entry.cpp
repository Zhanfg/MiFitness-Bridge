// Copyright 2026 MiFitness-Bridge contributors.
// Native Zygisk Next app loader. No Xposed/LSPosed framework or API involved.
// ART gates are version-pinned and fail closed; nothing is injected into system_server.
#include <sys/types.h>
#include "zygisk.hpp"
#include <android/log.h>
#include <dobby.h>
#include <lsplant.hpp>
#include <xdl.h>
#include <jni.h>
#include <fcntl.h>
#include <elf.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstring>
#include <string>
#include <string_view>
#include <pthread.h>
#include <vector>
#include <atomic>
#include <fstream>
#include <sstream>
#include <mutex>
#include <unordered_map>

namespace {
constexpr const char *kTag="MiFitnessBridge";
constexpr const char *kTarget="com.mi.health";
constexpr const char *kDevice="com.mi.health:device";
constexpr size_t kMaxDex=4u*1024u*1024u;
JavaVM *vm=nullptr;
jclass activity_thread_class=nullptr;
jmethodID current_application_id=nullptr;
std::vector<unsigned char> dex;
void *art=nullptr;
std::atomic<bool> ready{false};
bool enable_calendar=false;
bool fail_on_conflict=true;

void log_msg(int level,const char *text) {
    __android_log_write(level,kTag,text);
}
void clear(JNIEnv *env,const char *context) {
    if(env->ExceptionCheck()) {
        env->ExceptionClear();
        __android_log_print(ANDROID_LOG_WARN,kTag,"JNI error in %s",context);
    }
}
bool file_read(int dir,const char *name,std::vector<unsigned char> *out) {
    int fd=openat(dir,name,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return false;
    struct stat s{};
    if(fstat(fd,&s)!=0||s.st_size<=0||static_cast<size_t>(s.st_size)>kMaxDex) {
        close(fd);return false;
    }
    out->resize(static_cast<size_t>(s.st_size));
    size_t n=0;
    while(n<out->size()) {
        ssize_t r=read(fd,out->data()+n,out->size()-n);
        if(r<=0){close(fd);out->clear();return false;}
        n+=static_cast<size_t>(r);
    }
    close(fd);return true;
}
bool read_config(int dir) {
    int fd=openat(dir,"bridge.conf",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return false;
    char buf[1025]{};
    ssize_t n=read(fd,buf,1024);
    close(fd);
    if(n<=0||n>=1024)return false;
    buf[n]=0;
    std::string str(buf,static_cast<size_t>(n));
    enable_calendar=false;
    fail_on_conflict=true;
    std::istringstream stream(str);
    std::string line;
    while(std::getline(stream,line)) {
        if(line=="calendar_hook=1")enable_calendar=true;
        if(line=="fail_on_conflict=0")fail_on_conflict=false;
    }
    return true;
}
bool conflicting_runtime() {
    if(!fail_on_conflict)return false;
    std::ifstream maps("/proc/self/maps");
    std::string line;
    while(std::getline(maps,line)) {
        if(line.find("libxposed")!=std::string::npos||
           line.find("liblsposed")!=std::string::npos||
           line.find("zygisk_vector")!=std::string::npos) return true;
    }
    return false;
}
jclass load_class(JNIEnv *env,jobject loader,const char *name) {
    if(!loader)return nullptr;
    jclass cl=env->FindClass("java/lang/ClassLoader");
    if(!cl){clear(env,"ClassLoader");return nullptr;}
    jmethodID method=env->GetMethodID(cl,"loadClass","(Ljava/lang/String;)Ljava/lang/Class;");
    if(!method){clear(env,"ClassLoader.loadClass");env->DeleteLocalRef(cl);return nullptr;}
    jstring jname=env->NewStringUTF(name);
    jobject result=env->CallObjectMethod(loader,method,jname);
    if(env->ExceptionCheck()){env->ExceptionClear();result=nullptr;}
    env->DeleteLocalRef(jname);env->DeleteLocalRef(cl);
    return reinterpret_cast<jclass>(result);
}
jobject get_application(JNIEnv *env) {
    if(activity_thread_class && current_application_id) {
        jobject app=env->CallStaticObjectMethod(activity_thread_class,current_application_id);
        clear(env,"cached ActivityThread.currentApplication");
        return app;
    }
    jclass cl=env->FindClass("android/app/ActivityThread");
    if(!cl){clear(env,"ActivityThread");return nullptr;}
    jmethodID m=env->GetStaticMethodID(cl,"currentApplication","()Landroid/app/Application;");
    if(!m){clear(env,"currentApplication");env->DeleteLocalRef(cl);return nullptr;}
    jobject app=env->CallStaticObjectMethod(cl,m);
    clear(env,"currentApplication()");
    env->DeleteLocalRef(cl);
    return app;
}
jobject app_loader(JNIEnv *env,jobject app) {
    jclass cl=env->GetObjectClass(app);
    if(!cl)return nullptr;
    jmethodID m=env->GetMethodID(cl,"getClassLoader","()Ljava/lang/ClassLoader;");
    if(!m){clear(env,"getClassLoader");env->DeleteLocalRef(cl);return nullptr;}
    jobject loader=env->CallObjectMethod(app,m);
    clear(env,"getClassLoader()");env->DeleteLocalRef(cl);
    return loader;
}
jobject dex_loader(JNIEnv *env,jobject parent) {
    if(dex.empty())return nullptr;
    jobject mem=env->NewDirectByteBuffer(dex.data(),static_cast<jlong>(dex.size()));
    if(!mem)return nullptr;
    jclass cl=env->FindClass("dalvik/system/InMemoryDexClassLoader");
    if(!cl){clear(env,"InMemoryDexClassLoader");env->DeleteLocalRef(mem);return nullptr;}
    jmethodID ctor=env->GetMethodID(cl,"<init>","(Ljava/nio/ByteBuffer;Ljava/lang/ClassLoader;)V");
    if(!ctor){clear(env,"DexLoader constructor");env->DeleteLocalRef(cl);env->DeleteLocalRef(mem);return nullptr;}
    jobject result=env->NewObject(cl,ctor,mem,parent);
    clear(env,"Create DexLoader");
    env->DeleteLocalRef(cl);env->DeleteLocalRef(mem);
    return result;
}
jobject do_hook(JNIEnv *env,jclass,jobject method,jobject obj,jobject callback) {
    if(!ready.load(std::memory_order_acquire))return nullptr;
    return lsplant::Hook(env,method,obj,callback);
}
jboolean do_unhook(JNIEnv *env,jclass,jobject method) {
    return ready.load(std::memory_order_acquire) && lsplant::UnHook(env,method) ? JNI_TRUE:JNI_FALSE;
}
jboolean do_deopt(JNIEnv *env,jclass,jobject method) {
    return ready.load(std::memory_order_acquire) && lsplant::Deoptimize(env,method) ? JNI_TRUE:JNI_FALSE;
}
void do_log(JNIEnv *env,jclass,jint level,jstring message) {
    if(!message)return;
    const char *s=env->GetStringUTFChars(message,nullptr);
    if(s){__android_log_write(level,kTag,s);env->ReleaseStringUTFChars(message,s);}
}
bool register_bridge(JNIEnv *env,jobject loader) {
    jclass c=load_class(env,loader,"dev.axymorrsen.mifitness.NativeBridge");
    if(!c)return false;
    JNINativeMethod methods[]={
        {const_cast<char*>("hook"),const_cast<char*>("(Ljava/lang/reflect/Method;Ljava/lang/Object;Ljava/lang/reflect/Method;)Ljava/lang/reflect/Method;"),reinterpret_cast<void*>(do_hook)},
        {const_cast<char*>("unhook"),const_cast<char*>("(Ljava/lang/reflect/Method;)Z"),reinterpret_cast<void*>(do_unhook)},
        {const_cast<char*>("deoptimize"),const_cast<char*>("(Ljava/lang/reflect/Method;)Z"),reinterpret_cast<void*>(do_deopt)},
        {const_cast<char*>("log"),const_cast<char*>("(ILjava/lang/String;)V"),reinterpret_cast<void*>(do_log)}
    };
    bool ok=env->RegisterNatives(c,methods,4)==JNI_OK;
    clear(env,"RegisterNatives");env->DeleteLocalRef(c);
    return ok;
}
void *art_exact(std::string_view name) {
    if(!art)return nullptr;
    std::string key(name);
    void *p=xdl_sym(art,key.c_str(),nullptr);
    return p?p:xdl_dsym(art,key.c_str(),nullptr);
}
// Look up full symbol names matching ART prefixes. Validate all ELF boundaries
// before touching the mapped on-disk section tables. No guessed addresses.
// The ART symbol resolver is consulted repeatedly during initialization.
// Keep a single bounded read-only ELF mapping and memoize prefix results.
// These files do not contain user data; no ELF bytes are modified.
struct ArtSymbolIndex {
    const unsigned char *base=nullptr;
    size_t size=0;
    bool attempted=false;
    std::unordered_map<std::string,void*> cache;
    std::mutex lock;
};
ArtSymbolIndex symbol_index;

bool prepare_art_symbol_index() {
    if(symbol_index.attempted)return symbol_index.base!=nullptr;
    symbol_index.attempted=true;
    std::ifstream maps("/proc/self/maps");
    std::string line,path;
    while(std::getline(maps,line)) {
        const size_t pos=line.find("/apex/");
        if(pos==std::string::npos || line.find("/libart.so",pos)==std::string::npos)continue;
        const size_t end=line.find("/libart.so",pos)+strlen("/libart.so");
        path=line.substr(pos,end-pos);
        break;
    }
    if(path.empty())return false;
    const int fd=open(path.c_str(),O_RDONLY|O_CLOEXEC); // APEX libraries may use system-managed symlinks.
    if(fd<0)return false;
    struct stat st{};
    if(fstat(fd,&st)!=0 ||
       st.st_size<static_cast<off_t>(sizeof(Elf64_Ehdr)) ||
       st.st_size>static_cast<off_t>(256u*1024u*1024u)) {
        close(fd);
        return false;
    }
    const size_t size=static_cast<size_t>(st.st_size);
    const void *mapped=mmap(nullptr,size,PROT_READ,MAP_PRIVATE,fd,0);
    close(fd);
    if(mapped==MAP_FAILED)return false;
    symbol_index.base=static_cast<const unsigned char*>(mapped);
    symbol_index.size=size;
    return true;
}

void *art_prefix(std::string_view prefix) {
    if(!art || prefix.empty())return nullptr;
    std::lock_guard<std::mutex> guard(symbol_index.lock);
    const std::string key(prefix);
    const auto prev=symbol_index.cache.find(key);
    if(prev!=symbol_index.cache.end())return prev->second;
    if(!prepare_art_symbol_index())return nullptr;
    const unsigned char *begin=symbol_index.base;
    const size_t size=symbol_index.size;
    auto within=[&](uint64_t off,uint64_t len)->bool {
        return off<=size && len<=size-static_cast<size_t>(off);
    };
    void *result=nullptr;
    const auto *eh=reinterpret_cast<const Elf64_Ehdr*>(begin);
    if(memcmp(eh->e_ident,ELFMAG,SELFMAG)==0 &&
       eh->e_ident[EI_CLASS]==ELFCLASS64 &&
       eh->e_shentsize==sizeof(Elf64_Shdr) &&
       eh->e_shnum>0 &&
       within(eh->e_shoff,static_cast<uint64_t>(eh->e_shnum)*sizeof(Elf64_Shdr))){
        const auto *sh=reinterpret_cast<const Elf64_Shdr*>(begin+eh->e_shoff);
        for(unsigned i=0;i<eh->e_shnum&&!result;i++){
            if((sh[i].sh_type!=SHT_SYMTAB && sh[i].sh_type!=SHT_DYNSYM) ||
               sh[i].sh_entsize!=sizeof(Elf64_Sym)||sh[i].sh_link>=eh->e_shnum ||
               !within(sh[i].sh_offset,sh[i].sh_size))continue;
            const auto &str=sh[sh[i].sh_link];
            if(str.sh_type!=SHT_STRTAB||!within(str.sh_offset,str.sh_size))continue;
            const auto *syms=reinterpret_cast<const Elf64_Sym*>(begin+sh[i].sh_offset);
            const auto *names=reinterpret_cast<const char*>(begin+str.sh_offset);
            const size_t count=sh[i].sh_size/sizeof(Elf64_Sym);
            for(size_t j=0;j<count;j++){
                if(syms[j].st_name>=str.sh_size || syms[j].st_shndx==SHN_UNDEF)continue;
                const char *name=names+syms[j].st_name;
                const size_t remain=str.sh_size-syms[j].st_name;
                const char *end=static_cast<const char*>(memchr(name,0,remain));
                if(!end)continue;
                const std::string_view candidate(name,static_cast<size_t>(end-name));
                if(candidate.size()<prefix.size() || candidate.substr(0,prefix.size())!=prefix)continue;
                result=xdl_sym(art,name,nullptr);
                if(!result)result=xdl_dsym(art,name,nullptr);
                if(result)break;
            }
        }
    }
    symbol_index.cache.emplace(key,result);
    return result;
}

bool init_art(JNIEnv *env) {
    art=xdl_open("libart.so",XDL_DEFAULT);
    if(!art)art=xdl_open("/apex/com.android.art/lib64/libart.so",XDL_DEFAULT);
    if(!art)return false;
    lsplant::InitInfo info;
    info.inline_hooker=[](void *target,void *hooker)->void* {
        dobby_dummy_func_t old=nullptr;
        if(DobbyHook(target,reinterpret_cast<dobby_dummy_func_t>(hooker),&old)!=0)return nullptr;
        return reinterpret_cast<void*>(old);
    };
    info.inline_unhooker=[](void *target)->bool{return DobbyDestroy(target)==0;};
    info.art_symbol_resolver=art_exact;
    info.art_symbol_prefix_resolver=art_prefix;
    info.generated_class_name="MiFitnessBridgeGate_";
    info.generated_source_name="MiFitnessBridge";
    info.generated_field_name="delegate";
    info.generated_method_name="{target}";
    if(!lsplant::Init(env,info))return false;
    ready.store(true,std::memory_order_release);
    return true;
}
void worker() {
    JNIEnv *env=nullptr;
    if(!vm||vm->AttachCurrentThread(&env,nullptr)!=JNI_OK||!env){log_msg(ANDROID_LOG_ERROR,"ART attach failed");return;}
    // Do not run against Zygote's ClassLoader: wait for target Application.
    jobject app=nullptr;
    for(int i=0;i<200;i++){
        app=get_application(env);
        if(app)break;
        usleep(50 * 1000);
    }
    if(!app){log_msg(ANDROID_LOG_ERROR,"Target Application did not initialize");vm->DetachCurrentThread();return;}
    if(conflicting_runtime()){
        log_msg(ANDROID_LOG_WARN,"Conflicting ART injection engine detected; no hooks installed");
        env->DeleteLocalRef(app);vm->DetachCurrentThread();return;
    }
    jobject parent=app_loader(env,app);
    jobject child=parent?dex_loader(env,parent):nullptr;
    if(parent)env->DeleteLocalRef(parent);
    if(!child){log_msg(ANDROID_LOG_ERROR,"Module Dex loader unavailable");env->DeleteLocalRef(app);vm->DetachCurrentThread();return;}
    if(!register_bridge(env,child)||!init_art(env)){
        log_msg(ANDROID_LOG_ERROR,"Native bridge or ART initialization failed; no app hooks");
        env->DeleteLocalRef(child);env->DeleteLocalRef(app);vm->DetachCurrentThread();return;
    }
    jclass gate=load_class(env,child,"dev.axymorrsen.mifitness.CalendarHook");
    if(gate){
        jmethodID method=env->GetStaticMethodID(gate,"install","(Landroid/app/Application;Z)V");
        if(method) {
            env->CallStaticVoidMethod(gate,method,app,static_cast<jboolean>(enable_calendar));
            clear(env,"CalendarHook.install");
        } else clear(env,"CalendarHook.install method");
        env->DeleteLocalRef(gate);
    } else log_msg(ANDROID_LOG_ERROR,"CalendarHook class unavailable");
    // Keep native code and DEX storage alive for installed ART callbacks.
    env->DeleteLocalRef(child);env->DeleteLocalRef(app);
    vm->DetachCurrentThread();
}
// pthread_create returns an error code instead of throwing std::system_error.
// C++ exceptions are disabled for this native Android library.
void *worker_entry(void *) {
    worker();
    return nullptr;
}
bool start_worker() {
    pthread_t thread{};
    const int error=pthread_create(&thread,nullptr,worker_entry,nullptr);
    if(error!=0) {
        __android_log_print(ANDROID_LOG_ERROR,kTag,
                            "Native background bootstrap unavailable (pthread error=%d)",error);
        return false;
    }
    pthread_detach(thread);
    return true;
}
}

class MiFitnessModule final:public zygisk::ModuleBase {
public:
    void onLoad(zygisk::Api *api,JNIEnv *env) override {api_=api; env_=env;env->GetJavaVM(&vm);}
    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        if(!api_||!env_||!args||!args->nice_name)return;
        const char *n=env_->GetStringUTFChars(args->nice_name,nullptr);
        if(!n)return;
        target_ = strcmp(n,kTarget)==0 || strcmp(n,kDevice)==0;
        env_->ReleaseStringUTFChars(args->nice_name,n);
        if(!target_){api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);return;}
        const int dir=api_->getModuleDir();
        if(dir<0){target_=false;api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);return;}
        const bool cfg=read_config(dir);
        const bool payload=file_read(dir,"classes.dex",&dex);
        close(dir);
        if(!cfg||!payload||!enable_calendar){
            target_=false;dex.clear();api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);return;
        }
        // Resolve the non-SDK ActivityThread method before application sandboxing.
        // In post-specialize, use the cached jmethodID; still fail safely if unavailable.
        jclass activity=env_->FindClass("android/app/ActivityThread");
        if(activity) {
            current_application_id=env_->GetStaticMethodID(
                activity,"currentApplication","()Landroid/app/Application;");
            if(current_application_id) {
                activity_thread_class=static_cast<jclass>(env_->NewGlobalRef(activity));
            } else clear(env_,"pre-specialization ActivityThread.currentApplication");
            env_->DeleteLocalRef(activity);
        } else clear(env_,"pre-specialization ActivityThread");
    }
    void postAppSpecialize(const zygisk::AppSpecializeArgs *) override {
        if(target_) {
            log_msg(ANDROID_LOG_INFO,"Native Zygisk Next attached in app/device process; initializing calendar bridge");
            start_worker();
        }
    }
    void preServerSpecialize(zygisk::ServerSpecializeArgs *) override {
        if(api_)api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);
    }
private:
    zygisk::Api *api_=nullptr;
    JNIEnv *env_=nullptr;
    bool target_=false;
};
REGISTER_ZYGISK_MODULE(MiFitnessModule)
