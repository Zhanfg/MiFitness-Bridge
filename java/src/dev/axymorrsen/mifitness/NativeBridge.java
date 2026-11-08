package dev.axymorrsen.mifitness;
import java.lang.reflect.Method;

/** All sensitive ART operations are executed in-process by our own native library.
 * This is not an Xposed or LSPosed API facade.
 */
final class NativeBridge {
    static final int INFO=4, WARN=5, ERROR=6;
    private NativeBridge() {}
    static native Method hook(Method target, Object hooker, Method callback);
    static native boolean unhook(Method target);
    static native boolean deoptimize(Method method);
    static native void log(int level, String text);
}
