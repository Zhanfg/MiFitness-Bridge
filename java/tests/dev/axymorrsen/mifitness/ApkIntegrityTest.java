package dev.axymorrsen.mifitness;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;

/** Host-only synthetic fixture; no Xiaomi APK or personal data is used. */
public final class ApkIntegrityTest {
    private ApkIntegrityTest() {}
    private static String digest(byte[] bytes) throws Exception {
        byte[] sha=MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder hex=new StringBuilder(64);
        for(byte b:sha) hex.append(String.format(java.util.Locale.ROOT,"%02x",b&0xff));
        return hex.toString();
    }
    public static void main(String[] args) throws Exception {
        File file=File.createTempFile("mifitness-fixture-", ".apk");
        try {
            byte[] original="synthetic APK bytes only".getBytes(StandardCharsets.UTF_8);
            try (FileOutputStream stream=new FileOutputStream(file)) {
                stream.write(original);
            }
            String reviewed=digest(original);
            if(!ApkIntegrity.matchesDigest(file,reviewed))
                throw new AssertionError("Valid byte-identical file rejected");
            if(ApkIntegrity.matchesDigest(file,ApkIntegrity.REVIEWED_SHA256))
                throw new AssertionError("Synthetic APK must not match Xiaomi baseline");
            Files.write(file.toPath(),"changed bytes".getBytes(StandardCharsets.UTF_8));
            if(ApkIntegrity.matchesDigest(file,reviewed))
                throw new AssertionError("Modified file accepted");
            if(!ApkIntegrity.isSinglePackage(null) ||
               !ApkIntegrity.isSinglePackage(new String[0]) ||
               ApkIntegrity.isSinglePackage(new String[] {"split_config.apk"}))
                throw new AssertionError("Split package handling invalid");
        } finally {
            file.delete();
        }
        System.out.println("ApkIntegrity reviewed bytes, mutation and split tests passed");
    }
}
