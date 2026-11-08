package dev.axymorrsen.mifitness;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

/** Exact Mi Fitness 3.59.2 DEX ABI. No Android SDK or runtime-dependent classes. */
public final class TargetResolver {
    private TargetResolver() {}

    public static final class Gates {
        public final Class<?> modelType;
        public final Method isSupportFeature;
        public final Method[] methods;

        private Gates(Class<?> model, Method feature, Method[] targets) {
            modelType = model;
            isSupportFeature = feature;
            methods = targets;
        }
    }

    private static Class<?> type(ClassLoader loader, String name)
            throws ClassNotFoundException {
        return loader.loadClass(name);
    }

    private static Method exact(Class<?> holder, String name, boolean isStatic,
                                Class<?>... parameters) throws NoSuchMethodException {
        Method method = holder.getDeclaredMethod(name, parameters);
        if (method.getReturnType() != boolean.class ||
                Modifier.isStatic(method.getModifiers()) != isStatic) {
            throw new NoSuchMethodException(holder.getName() + "." + name +
                    " return/static contract changed");
        }
        method.setAccessible(true);
        return method;
    }

    public static Gates resolveGates(ClassLoader loader)
            throws ReflectiveOperationException {
        Class<?> model = type(loader,
                "com.xiaomi.fitness.device.manager.export.WearableDeviceModel");
        Class<?> baseModel = type(loader,
                "com.xiaomi.fitness.device.manager.DeviceModel");
        if (!baseModel.isAssignableFrom(model)) {
            throw new NoSuchMethodException("WearableDeviceModel no longer a DeviceModel");
        }
        Class<?> features = type(loader,
                "com.xiaomi.fitness.device.manager.DeviceModelExtKt");
        Method feature = exact(features, "isSupportFeature", true,
                baseModel, String.class);

        Method[] gates = new Method[3];
        gates[0] = exact(type(loader,
                "com.xiaomi.fitness.device.manager.extensions.DeviceModelExtKt"),
                "isSupportSyncPhoneSchedule", true, model);
        gates[1] = exact(type(loader,
                "com.xiaomi.fitness.devicesettings.di.FeatureItemModule"),
                "createSyncScheduleItem$lambda$59", true, model);
        gates[2] = exact(type(loader,
                "com.xiaomi.fitness.devicesettings.di.DeviceSettingsSyncHelperImpl"),
                "isCalendarSyncAndroidVersion", false);
        return new Gates(model, feature, gates);
    }

    public static final class WearableManagerReader {
        private final Object manager;
        private final Method getter;

        private WearableManagerReader(Object manager, Method getter) {
            this.manager = manager;
            this.getter = getter;
        }

        public Object getCurrentModel() throws ReflectiveOperationException {
            return getter.invoke(manager);
        }
    }

    public static WearableManagerReader resolveWearableManager(ClassLoader loader)
            throws ReflectiveOperationException {
        Class<?> type = type(loader,
                "com.xiaomi.fitness.device.manager.export.WearableDeviceManager");
        Class<?> companionType = type(loader,
                "com.xiaomi.fitness.device.manager.export.WearableDeviceManager$Companion");
        Class<?> extensionType = type(loader,
                "com.xiaomi.fitness.device.manager.export.DeviceManagerExtKt");
        Field companion = type.getDeclaredField("Companion");
        companion.setAccessible(true);
        Object token = companion.get(null);
        Method factory = extensionType.getDeclaredMethod("getInstance", companionType);
        factory.setAccessible(true);
        Object manager = factory.invoke(null, token);
        if (manager == null || !type.isInstance(manager)) {
            throw new NoSuchMethodException("WearableDeviceManager factory returned wrong type");
        }
        Method getter = manager.getClass().getMethod("getCurrentDeviceModel");
        if (getter.getParameterTypes().length != 0) {
            throw new NoSuchMethodException("Current model getter ABI changed");
        }
        getter.setAccessible(true);
        return new WearableManagerReader(manager, getter);
    }
}
