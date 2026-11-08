package dev.axymorrsen.mifitness;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.util.Locale;

/** Startup-only APK content gate. Reads the APK file, never private app data. */
public final class ApkIntegrity {
    public static final String REVIEWED_SHA256 =
        "112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d";
    private static final long MAX_BYTES = 512L * 1024L * 1024L;
    private ApkIntegrity() {}

    public static boolean matchesReviewed(File apk) {
        if (apk == null || !apk.isFile() || !apk.canRead()) return false;
        long length = apk.length();
        if (length <= 0 || length > MAX_BYTES) return false;
        try (FileInputStream stream = new FileInputStream(apk)) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[128 * 1024];
            long total = 0;
            int read;
            while ((read = stream.read(buffer)) != -1) {
                total += read;
                if (total > MAX_BYTES) return false;
                digest.update(buffer, 0, read);
            }
            if (total != length) return false;
            byte[] actual = digest.digest();
            byte[] expected = parseDigest(REVIEWED_SHA256);
            return MessageDigest.isEqual(actual, expected);
        } catch (Exception ignored) {
            return false;
        }
    }

    public static boolean isSinglePackage(String[] splitSourceDirs) {
        return splitSourceDirs == null || splitSourceDirs.length == 0;
    }

    static byte[] parseDigest(String hex) {
        if (hex == null || hex.length() != 64) throw new IllegalArgumentException("hash");
        byte[] digest = new byte[32];
        for (int i = 0; i < digest.length; i++) {
            int hi = Character.digit(hex.charAt(i * 2), 16);
            int lo = Character.digit(hex.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) throw new IllegalArgumentException("hash");
            digest[i] = (byte) ((hi << 4) | lo);
        }
        return digest;
    }
}
