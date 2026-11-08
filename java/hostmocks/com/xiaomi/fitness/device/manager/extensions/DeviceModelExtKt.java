package com.xiaomi.fitness.device.manager.extensions;
import com.xiaomi.fitness.device.manager.export.WearableDeviceModel;
public final class DeviceModelExtKt {
    public static boolean isSupportSyncPhoneSchedule(WearableDeviceModel device) {
        return device != null;
    }
    // Decoy: must never be selected by ABI resolver.
    public static boolean isSupportSyncPhoneSchedule(Object device) {
        throw new AssertionError("Wrong overload selected");
    }
}
