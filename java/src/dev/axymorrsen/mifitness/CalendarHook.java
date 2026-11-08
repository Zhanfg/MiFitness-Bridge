package dev.axymorrsen.mifitness;

import android.Manifest;
import android.app.Application;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import java.lang.reflect.InvocationTargetException;
import android.content.pm.Signature;
import java.security.MessageDigest;
import java.lang.ref.WeakReference;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;

/**
 * Mi Fitness 3.59.2 only. All three hooks are resolved before attempting installation.
 * Invocation follows the original method first; only an original false can be elevated.
 */
public final class CalendarHook {
    private static final int PINNED_VERSION = 359002;
    private static final String PINNED_SIGNER = "c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025";
    private static final String APP = "com.mi.health";
    private static final String MODEL = "com.xiaomi.fitness.device.manager.export.WearableDeviceModel";
    private static final String CAPABILITY = "com.xiaomi.fitness.device.manager.DeviceModelExtKt";
    private static final String[] GATE_CLASSES = {
        "com.xiaomi.fitness.device.manager.extensions.DeviceModelExtKt",
        "com.xiaomi.fitness.devicesettings.di.FeatureItemModule",
        "com.xiaomi.fitness.devicesettings.di.DeviceSettingsSyncHelperImpl"
    };
    private static final String[] GATE_METHODS = {
        "isSupportSyncPhoneSchedule",
        "createSyncScheduleItem$lambda$59",
        "isCalendarSyncAndroidVersion"
    };
    private final Application app;
    private final Method isSupportFeature;
    private final Method[] targets;
    private final Object[] callbacks;
    private final List<Method> installed = new ArrayList<>(3);
    private volatile boolean enabled;
    private volatile WeakReference<Object> lastCapableModel = new WeakReference<>(null);

    private CalendarHook(Application a, Method feature, Method[] methods) {
        this.app = a; this.isSupportFeature = feature; this.targets = methods;
        this.callbacks = new Object[] {new Callback(0), new Callback(1), new Callback(2)};
    }

    public static void install(Application app, boolean configEnabled) {
        if (!configEnabled || app == null || !APP.equals(app.getPackageName())) return;
        try {
            if (Build.VERSION.SDK_INT != 37 || !"PJZ110".equalsIgnoreCase(Build.MODEL)) {
                NativeBridge.log(NativeBridge.WARN, "Unsupported ROM/device; hooks disabled");
                return;
            }
            PackageInfo info = app.getPackageManager().getPackageInfo(
                    APP, PackageManager.GET_SIGNING_CERTIFICATES);
            if (info.versionCode != PINNED_VERSION || !signerMatches(info)) {
                NativeBridge.log(NativeBridge.WARN, "Mi Fitness version/signature mismatch; hooks disabled");
                return;
            }
            ClassLoader loader = app.getClassLoader();
            Class<?> model = loader.loadClass(MODEL);
            Class<?> ext = loader.loadClass(CAPABILITY);
            Method feature = ext.getDeclaredMethod("isSupportFeature", model, String.class);
            feature.setAccessible(true);
            Method[] methods = new Method[3];
            for (int i=0;i<methods.length;i++) {
                Class<?> holder = loader.loadClass(GATE_CLASSES[i]);
                methods[i] = (i==2)
                    ? holder.getDeclaredMethod(GATE_METHODS[i])
                    : holder.getDeclaredMethod(GATE_METHODS[i], model);
                methods[i].setAccessible(true);
                if (methods[i].getReturnType()!=boolean.class ||
                    Modifier.isStatic(methods[i].getModifiers())!=(i!=2)) {
                    NativeBridge.log(NativeBridge.ERROR, "Gate ABI mismatch: "+i);
                    return;
                }
            }
            CalendarHook hook = new CalendarHook(app, feature, methods);
            if (!hook.calendarReady()) {
                NativeBridge.log(NativeBridge.WARN, "Calendar Provider or READ_CALENDAR unavailable; hooks disabled");
                return;
            }
            Method callback = Callback.class.getDeclaredMethod("invoke", Object[].class);
            callback.setAccessible(true);
            for (int i=0;i<methods.length;i++) {
                Callback c = (Callback) hook.callbacks[i];
                c.backup = NativeBridge.hook(methods[i], c, callback);
                if (c.backup==null) {
                    NativeBridge.log(NativeBridge.ERROR, "Failed to install gate: "+i+"; rolling back");
                    hook.rollback();
                    return;
                }
                hook.installed.add(methods[i]);
            }
            hook.enabled = true;
            NativeBridge.log(NativeBridge.INFO, "Calendar gates 3/3 installed, version=359002, ROM=ColorOS17");
        } catch (Throwable t) {
            NativeBridge.log(NativeBridge.ERROR, "Calendar gate resolution failed: "+t.getClass().getSimpleName());
        }
    }

    private static boolean signerMatches(PackageInfo info) {
        try {
            if (info.signingInfo==null) return false;
            Signature[] s = info.signingInfo.getApkContentsSigners();
            if (s==null || s.length!=1) return false;
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(s[0].toByteArray());
            StringBuilder hex = new StringBuilder(64);
            for(byte b:digest) hex.append(String.format(java.util.Locale.ROOT,"%02x",b & 0xff));
            return PINNED_SIGNER.equals(hex.toString());
        } catch(Throwable ignored) {return false;}
    }

    private void rollback() {
        for (int i=installed.size()-1;i>=0;i--) NativeBridge.unhook(installed.get(i));
        installed.clear();
        enabled=false;
    }

    private boolean calendarReady() {
        try {
            return app.checkSelfPermission(Manifest.permission.READ_CALENDAR)
                    == PackageManager.PERMISSION_GRANTED &&
                   app.getPackageManager().resolveContentProvider("com.android.calendar",0)!=null;
        } catch(Throwable ignored) { return false; }
    }
    private boolean supportsCalendar(Object model) {
        if (model == null) return false;
        try {
            Object value=isSupportFeature.invoke(null,model,"calendar");
            return Boolean.TRUE.equals(value);
        } catch(Throwable ignored) {return false;}
    }
    private Object currentWearable() {
        try {
            ClassLoader loader=app.getClassLoader();
            Class<?> manager=loader.loadClass("com.xiaomi.fitness.device.manager.export.WearableDeviceManager");
            Class<?> managerExt=loader.loadClass("com.xiaomi.fitness.device.manager.export.DeviceManagerExtKt");
            Object companion=manager.getDeclaredField("Companion").get(null);
            Method getter=null;
            for(Method m: managerExt.getDeclaredMethods()) if (m.getName().equals("getInstance") && m.getParameterTypes().length==1) {getter=m;break;}
            if(getter==null) return null;
            getter.setAccessible(true);
            Object instance=getter.invoke(null,companion);
            Method current=instance.getClass().getMethod("getCurrentDeviceModel");
            return current.invoke(instance);
        } catch(Throwable ignored) {return null;}
    }

    /** LSPlant requires Object invoke(Object[]); no Xposed API used. */
    public final class Callback {
        private final int gate;
        private volatile Method backup;
        private Callback(int id) {gate=id;}
        public Object invoke(Object[] args) throws Throwable {
            Method original=backup;
            if (original==null) return Boolean.FALSE;
            try {
                Object receiver=(gate==2) ? args[0] : null;
                Object[] parameters = (gate==2) ? new Object[0] : new Object[]{args[0]};
                boolean before=Boolean.TRUE.equals(original.invoke(receiver,parameters));
                if(before || !enabled) return before;
                Object model=(gate==2) ? currentWearable() : args[0];
                if(model==null && gate==2) model=lastCapableModel.get();
                if(gate!=2 && supportsCalendar(model))
                    lastCapableModel = new WeakReference<>(model);
                return GatePolicy.allow(before,true,calendarReady(),supportsCalendar(model),true);
            } catch(InvocationTargetException e) {
                throw e.getCause();
            }
        }
    }
}
