package dev.axymorrsen.mifitness;

/** The only allowed behavior change: turn a false feature gate true after all checks.
 * Never turn true into false, and never spoof global ROM identity or BLE capabilities.
 */
public final class GatePolicy {
    private GatePolicy() {}
    public static boolean allow(boolean original, boolean enabled, boolean calendarReady,
                                boolean modelSupportsCalendar, boolean versionPinned) {
        return original || (enabled && calendarReady && modelSupportsCalendar && versionPinned);
    }
}
