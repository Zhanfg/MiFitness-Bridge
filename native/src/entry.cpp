// MiFitness-Bridge native probe: target-scoped Zygisk API (runtime supplied by Zygisk Next).
// No LSPosed dependency. This milestone installs no ART or JNI hooks.
#include <sys/types.h>
#include "zygisk.hpp"
#include <android/log.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>

namespace {
constexpr char kApp[] = "com.mi.health";
constexpr char kTag[] = "MiFitnessBridge";
constexpr char kConfig[] = "bridge.conf";
bool read_enabled_config(int module_fd) {
    if (module_fd < 0) return false;
    const int fd = openat(module_fd, kConfig, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    char content[256] = {};
    const ssize_t count = read(fd, content, sizeof(content) - 1);
    close(fd);
    if (count <= 0 || count >= static_cast<ssize_t>(sizeof(content) - 1)) return false;
    // Fixed literal key, not an arbitrary command parser; configuration cannot execute code.
    return strstr(content, "native_probe=1") != nullptr;
}
}  // namespace

class MiFitnessNative final : public zygisk::ModuleBase {
public:
    void onLoad(zygisk::Api *api, JNIEnv *env) override {
        api_ = api;
        env_ = env;
    }

    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        if (!api_ || !env_ || !args || !args->nice_name) return;
        const char *name = env_->GetStringUTFChars(args->nice_name, nullptr);
        if (!name) return;
        is_target_ = strcmp(name, kApp) == 0;
        env_->ReleaseStringUTFChars(args->nice_name, name);

        if (is_target_) {
            const int dir = api_->getModuleDir();
            emit_probe_ = read_enabled_config(dir);
            if (dir >= 0) close(dir);
        }

        // Diagnostic mode: no resident hooks yet, so unload after post-specialize.
        // Remove this option ONLY after implementing real hook lifetimes.
        api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);
    }

    void postAppSpecialize(const zygisk::AppSpecializeArgs *) override {
        if (is_target_ && emit_probe_) {
            __android_log_print(ANDROID_LOG_INFO, kTag,
                "Loaded for com.mi.health; native_probe=1; ART hooks=disabled; uid-scoped app process");
        }
    }

    void preServerSpecialize(zygisk::ServerSpecializeArgs *) override {
        if (api_) api_->setOption(zygisk::Option::DLCLOSE_MODULE_LIBRARY);
    }
private:
    zygisk::Api *api_ = nullptr;
    JNIEnv *env_ = nullptr;
    bool is_target_ = false;
    bool emit_probe_ = false;
};

REGISTER_ZYGISK_MODULE(MiFitnessNative)
