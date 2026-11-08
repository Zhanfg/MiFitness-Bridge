#!/usr/bin/env python3
"""Apply the LSPlant upstream Oct 31, 2026 UnHook ordering fix to the
pre-NDK-r30 (Android 17-compatible) pinned source, without changing ABI.
Upstream reference: LSPosed/LSPlant 06bd3412d639d6b0d76fe6c7388066fe44e8963d.
This file is a compatibility backport, not new upstream code.
"""
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = """    // FIXME: not atomic, but should be fine
    hooked_methods_.erase(backup);
    proxied_backup_methods_.erase(backup);
    hooked_classes_.erase_if(target->GetDeclaringClass()->GetClassDef(), [&target](auto &it) {
"""
new = """    hooked_classes_.erase_if(target->GetDeclaringClass()->GetClassDef(), [&target](auto &it) {
"""
if text.count(old)!=1:
    raise SystemExit("LSPlant source is not the vetted revision; refusing unsafe patch")
text = text.replace(old,new)
old2="""    auto *backup_method = env->FromReflectedMethod(reflected_backup);
    env->DeleteGlobalRef(reflected_backup);
"""
new2="""    // Encode the backup JNI id while LSPlant still tracks it. Android 17
    // debuggable ART may use opaque JNI IDs and require this ordering.
    auto *backup_method = env->FromReflectedMethod(reflected_backup);
    // FIXME: not atomic, as in upstream.
    hooked_methods_.erase(backup);
    proxied_backup_methods_.erase(backup);
    env->DeleteGlobalRef(reflected_backup);
"""
if text.count(old2)!=1:
    raise SystemExit("LSPlant UnHook target block changed; refusing unsafe patch")
path.write_text(text.replace(old2,new2),encoding="utf-8")
print("LSPlant backport: UnHook JNI ID ordering fix applied")
