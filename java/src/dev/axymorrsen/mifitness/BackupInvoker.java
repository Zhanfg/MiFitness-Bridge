package dev.axymorrsen.mifitness;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 * LSPlant v2's generated backup Method is STATIC, including for instance targets.
 * For an instance target it prepends the original receiver to the arguments.
 * The reflective invocation receiver must therefore ALWAYS be null.
 */
public final class BackupInvoker {
    private BackupInvoker() {}

    public static Object call(Method backup, Object[] packedArgs) throws Throwable {
        if (backup == null || packedArgs == null) {
            throw new IllegalStateException("Missing ART backup or arguments");
        }
        try {
            return backup.invoke(null, packedArgs);
        } catch (InvocationTargetException wrapped) {
            throw wrapped.getCause();
        }
    }
}
