package dev.axymorrsen.mifitness;

import java.lang.reflect.Method;

public final class BackupInvokerTest {
    private BackupInvokerTest() {}

    static final class Receiver {
        private final boolean value;
        Receiver(boolean value) { this.value = value; }
        boolean read() { return value; }
    }
    // Emulates LSPlant-generated static backup() for an instance boolean target.
    public static boolean instanceBackup(Object receiver) {
        return ((Receiver) receiver).read();
    }
    // Emulates LSPlant-generated static backup() for a static boolean target.
    public static boolean staticBackup(Object argument) {
        return Boolean.TRUE.equals(argument);
    }
    public static boolean exceptional(Object ignored) {
        throw new IllegalArgumentException("original exception");
    }
    public static void main(String[] args) throws Throwable {
        Method instance = BackupInvokerTest.class.getMethod("instanceBackup", Object.class);
        Method scalar = BackupInvokerTest.class.getMethod("staticBackup", Object.class);
        Method err = BackupInvokerTest.class.getMethod("exceptional", Object.class);

        if (!Boolean.TRUE.equals(BackupInvoker.call(instance, new Object[] {new Receiver(true)})))
            throw new AssertionError("instance backup true was lost");
        if (!Boolean.FALSE.equals(BackupInvoker.call(instance, new Object[] {new Receiver(false)})))
            throw new AssertionError("instance backup false was lost");
        if (!Boolean.TRUE.equals(BackupInvoker.call(scalar, new Object[] {Boolean.TRUE})))
            throw new AssertionError("static backup true was lost");
        if (!Boolean.FALSE.equals(BackupInvoker.call(scalar, new Object[] {Boolean.FALSE})))
            throw new AssertionError("static backup false was lost");
        try {
            BackupInvoker.call(err, new Object[] {Boolean.FALSE});
            throw new AssertionError("Original exception should propagate");
        } catch (IllegalArgumentException ex) {
            if (!"original exception".equals(ex.getMessage())) throw ex;
        }
        System.out.println("BackupInvoker static/instance/exception cases passed");
    }
}
