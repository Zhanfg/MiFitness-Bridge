package dev.axymorrsen.mifitness;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

public final class TargetResolverTest {
    private TargetResolverTest() {}
    public static void main(String[] ignored) throws Throwable {
        ClassLoader loader = TargetResolverTest.class.getClassLoader();
        TargetResolver.Gates g = TargetResolver.resolveGates(loader);
        if (g.methods.length != 3) throw new AssertionError("Unexpected gate count");
        String[] names = {
            "isSupportSyncPhoneSchedule", "createSyncScheduleItem$lambda$59",
            "isCalendarSyncAndroidVersion"
        };
        for (int i = 0; i < g.methods.length; i++) {
            Method m = g.methods[i];
            if (!names[i].equals(m.getName())) throw new AssertionError("Wrong target " + i);
            if (m.getReturnType() != boolean.class) throw new AssertionError("Bad return " + i);
            if (Modifier.isStatic(m.getModifiers()) != (i != 2))
                throw new AssertionError("Bad static bit " + i);
            if (m.getParameterCount() != (i == 2 ? 0 : 1))
                throw new AssertionError("Bad arg count " + i);
        }
        if (!g.isSupportFeature.getParameterTypes()[0].isAssignableFrom(g.modelType))
            throw new AssertionError("DeviceModel/WearableDeviceModel inheritance changed");
        TargetResolver.WearableManagerReader reader =
            TargetResolver.resolveWearableManager(loader);
        Object model = reader.getCurrentModel();
        if (!g.modelType.isInstance(model))
            throw new AssertionError("Current model is not a wearable model");
        if (!Boolean.TRUE.equals(g.isSupportFeature.invoke(null, model, "calendar")))
            throw new AssertionError("Calendar capability query failed");
        try {
            TargetResolver.resolveGates(new ClassLoader(null) {});
            throw new AssertionError("Missing target classes should be fatal");
        } catch (ClassNotFoundException expected) {
            // A mismatched version must disable the hooks, not run them blind.
        }
        System.out.println("TargetResolver gates/overloads/capability/missing-class tests passed");
    }
}
