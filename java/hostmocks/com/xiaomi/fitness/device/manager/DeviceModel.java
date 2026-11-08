package com.xiaomi.fitness.device.manager;
public class DeviceModel {}
class DeviceModelExtKt {
    public static boolean isSupportFeature(DeviceModel model, String capability) {
        return model != null && "calendar".equals(capability);
    }
}
