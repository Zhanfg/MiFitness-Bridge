package dev.axymorrsen.mifitness;

import android.Manifest;
import android.app.Application;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
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
    private final Application app;
    private final boolean providerPresent;
    private final Object deviceManagerLock = new Object();
    private volatile TargetResolver.WearableManagerReader cachedReader;
    private final Method isSupportFeature;
    private final Method[] targets;
    private final Object[] callbacks;
    private final List<Method> installed = new ArrayList<>(3);
    private volatile boolean enabled;
    private volatile WeakReference<Object> lastCapableModel = new WeakReference<>(null);

    private CalendarHook(Application a, Method feature, Method[] methods) {
        this.app = a;
        this.providerPresent = a.getPackageManager().resolveContentProvider("com.android.calendar", 0) != null;
        this.isSupportFeature = feature; this.targets = methods;
        this.callbacks = new Object[] {new Callback(0), new Callback(1), new Callback(2)};
    }

    public static void install(Application app, boolean configEnabled) {
        if (!configEnabled || app == null || !APP.equals(app.getPackageName())) return;
        CalendarHook hook = null;
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
            TargetResolver.Gates resolved = TargetResolver.resolveGates(loader);
            Class<?> model = resolved.modelType;
            Method feature = resolved.isSupportFeature;
            Method[] methods = resolved.methods;
            hook = new CalendarHook(app, feature, methods);
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
            int deoptCount = hook.deoptimizeKnownCallers(loader, model);
            NativeBridge.log(NativeBridge.INFO,
                "Calendar gates 3/3 installed, deoptimized_callers="+deoptCount+
                ", version=359002, ROM=ColorOS17");
        } catch (Throwable t) {
            if (hook != null) {
                try { hook.rollback(); } catch (Throwable ignored) {
                    NativeBridge.log(NativeBridge.ERROR, "Calendar rollback encountered an exception");
                }
            }
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

    private int deoptimizeKnownCallers(ClassLoader loader, Class<?> model) {
        // DEX-proven direct callers only; do not deoptimize the entire application.
        // ART may have AOT-inlined the previous gate result into a caller.
        int count=0;
        try {
            Class<?> ext=loader.loadClass(
                "com.xiaomi.fitness.device.manager.extensions.DeviceModelExtKt");
            Method caller=ext.getDeclaredMethod("getFeatureItemVisible", model, int.class);
            caller.setAccessible(true);
            if(NativeBridge.deoptimize(caller))count++;
        } catch(Throwable ignored) {
            NativeBridge.log(NativeBridge.WARN,"UI caller deoptimization unavailable");
        }
        try {
            Class<?> holder=loader.loadClass(
                "com.xiaomi.fitness.devicesettings.di.FeatureItemModule");
            Method caller=holder.getDeclaredMethod("O",model);
            caller.setAccessible(true);
            if(NativeBridge.deoptimize(caller))count++;
        } catch(Throwable ignored) {
            NativeBridge.log(NativeBridge.WARN,"Settings caller deoptimization unavailable");
        }
        try {
            Class<?> engine=loader.loadClass("com.xiaomi.fitness.sync.SyncEngine");
            Method caller=engine.getDeclaredMethod("isSyncCalendar",model);
            caller.setAccessible(true);
            if(NativeBridge.deoptimize(caller))count++;
            Method syncCaller=null;
            for(Method m:engine.getDeclaredMethods()) {
                if(m.getName().equals("syncCalendarToDevices") &&
                    m.getParameterTypes().length==4) {syncCaller=m;break;}
            }
            if(syncCaller!=null) {
                syncCaller.setAccessible(true);
                if(NativeBridge.deoptimize(syncCaller))count++;
            }
        } catch(Throwable ignored) {
            NativeBridge.log(NativeBridge.WARN,"Sync caller deoptimization unavailable");
        }
        return count;
    }

    private void rollback() {
        // Stop elevation before touching the non-atomic native UnHook lifecycle.
        enabled=false;
        int failures=0;
        for (int i=installed.size()-1;i>=0;i--) {
            try {
                if (!NativeBridge.unhook(installed.get(i))) failures++;
            } catch (Throwable ignored) {
                failures++;
            }
        }
        installed.clear();
        if(failures != 0) NativeBridge.log(NativeBridge.ERROR,
            "Partial ART rollback: "+failures+" method(s) could not be unhooked");
    }

    private boolean calendarReady() {
        // CalendarProvider is a system component; resolve it once on initialization.
        // Runtime permission must still be checked each time it can change.
        try {
            return providerPresent &&
                app.checkSelfPermission(Manifest.permission.READ_CALENDAR) ==
                    PackageManager.PERMISSION_GRANTED;
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
            TargetResolver.WearableManagerReader reader=cachedReader;
            if(reader==null) {
                synchronized (deviceManagerLock) {
                    reader=cachedReader;
                    if(reader==null) {
                        reader=TargetResolver.resolveWearableManager(app.getClassLoader());
                        cachedReader=reader;
                    }
                }
            }
            return reader.getCurrentModel();
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
            // LSPlant's backup is always static. For instance gates,
                // packedArgs[0] is the former receiver, not Method.invoke's receiver.
                boolean before=Boolean.TRUE.equals(BackupInvoker.call(original,args));
                if(before || !enabled) return before;
                Object model=(gate==2) ? currentWearable() : args[0];
                if(model==null && gate==2) model=lastCapableModel.get();
                if(gate!=2 && supportsCalendar(model))
                    lastCapableModel = new WeakReference<>(model);
                return GatePolicy.allow(before,true,calendarReady(),supportsCalendar(model),true);
        }
    }
}
