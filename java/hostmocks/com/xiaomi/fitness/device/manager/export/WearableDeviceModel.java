package com.xiaomi.fitness.device.manager.export;
public class WearableDeviceModel extends com.xiaomi.fitness.device.manager.DeviceModel {}
class WearableDeviceManager {
    public static final class Companion {}
    public static final Companion Companion = new Companion();
    public WearableDeviceModel getCurrentDeviceModel() {
        return new WearableDeviceModel();
    }
}
class BluetoothPermissionTool {
    public static final class Companion {}
}
class DeviceManagerExtKt {
    // A deliberately misleading overload, matching Mi Fitness's overloaded factory pattern.
    public static Object getInstance(BluetoothPermissionTool.Companion ignored) {
        throw new AssertionError("Wrong overload selected");
    }
    public static WearableDeviceManager getInstance(WearableDeviceManager.Companion ignored) {
        return new WearableDeviceManager();
    }
}
