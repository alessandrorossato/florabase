package io.github.alessandrorossato.florabase;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Stores the opaque Florabase device-session bearer token encrypted with a non-exportable
 * AES-256-GCM key held in AndroidKeyStore. Ciphertext + IV are persisted in app-private
 * SharedPreferences (with android:allowBackup="false"). Neither tokens nor ciphertexts are logged.
 */
@CapacitorPlugin(name = "SecureToken")
public class SecureTokenPlugin extends Plugin {

    private static final String KEYSTORE_PROVIDER = "AndroidKeyStore";
    private static final String KEY_ALIAS = "florabase_device_token_v1";
    private static final String PREFS_NAME = "florabase_secure_token";
    private static final String PREF_TOKEN_PAYLOAD = "device_token_v1";
    private static final String CIPHER_TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_IV_BYTES = 12;
    private static final int GCM_TAG_BITS = 128;
    private static final int MAX_DEVICE_LABEL_LENGTH = 120;

    private SharedPreferences getPrefs() {
        return getContext().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private SecretKey getOrCreateKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(KEYSTORE_PROVIDER);
        keyStore.load(null);
        KeyStore.Entry existing = keyStore.getEntry(KEY_ALIAS, null);
        if (existing instanceof KeyStore.SecretKeyEntry) {
            return ((KeyStore.SecretKeyEntry) existing).getSecretKey();
        }
        KeyGenerator generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            KEYSTORE_PROVIDER
        );
        KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .build();
        generator.init(spec);
        return generator.generateKey();
    }

    private SecretKey getExistingKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(KEYSTORE_PROVIDER);
        keyStore.load(null);
        KeyStore.Entry existing = keyStore.getEntry(KEY_ALIAS, null);
        if (existing instanceof KeyStore.SecretKeyEntry) {
            return ((KeyStore.SecretKeyEntry) existing).getSecretKey();
        }
        return null;
    }

    private void wipeStoredState() {
        try {
            getPrefs().edit().remove(PREF_TOKEN_PAYLOAD).commit();
        } catch (Exception ignored) {
            // Best-effort cleanup; never expose secrets or crash.
        }
        try {
            KeyStore keyStore = KeyStore.getInstance(KEYSTORE_PROVIDER);
            keyStore.load(null);
            if (keyStore.containsAlias(KEY_ALIAS)) {
                keyStore.deleteEntry(KEY_ALIAS);
            }
        } catch (Exception ignored) {
            // Best-effort key removal.
        }
    }

    @PluginMethod
    public void set(PluginCall call) {
        String token = call.getString("token");
        if (token == null || token.trim().isEmpty()) {
            call.reject("Token must be a non-empty string.");
            return;
        }
        try {
            SecretKey key = getOrCreateKey();
            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, key);
            byte[] iv = cipher.getIV();
            if (iv == null || iv.length != GCM_IV_BYTES) {
                call.reject("Unexpected cipher IV length.");
                return;
            }
            byte[] ciphertext = cipher.doFinal(token.getBytes(StandardCharsets.UTF_8));
            byte[] combined = new byte[iv.length + ciphertext.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(ciphertext, 0, combined, iv.length, ciphertext.length);
            String encoded = Base64.encodeToString(combined, Base64.NO_WRAP);
            boolean saved = getPrefs().edit().putString(PREF_TOKEN_PAYLOAD, encoded).commit();
            if (!saved) {
                call.reject("Failed to persist encrypted token.");
                return;
            }
            call.resolve();
        } catch (Exception error) {
            call.reject("Failed to store secure token.");
        }
    }

    @PluginMethod
    public void get(PluginCall call) {
        JSObject result = new JSObject();
        String encoded = getPrefs().getString(PREF_TOKEN_PAYLOAD, null);
        if (encoded == null || encoded.isEmpty()) {
            result.put("token", JSObject.NULL);
            call.resolve(result);
            return;
        }
        try {
            byte[] combined = Base64.decode(encoded, Base64.NO_WRAP);
            if (combined.length <= GCM_IV_BYTES) {
                wipeStoredState();
                result.put("token", JSObject.NULL);
                call.resolve(result);
                return;
            }
            SecretKey key = getExistingKey();
            if (key == null) {
                wipeStoredState();
                result.put("token", JSObject.NULL);
                call.resolve(result);
                return;
            }
            byte[] iv = new byte[GCM_IV_BYTES];
            byte[] ciphertext = new byte[combined.length - GCM_IV_BYTES];
            System.arraycopy(combined, 0, iv, 0, GCM_IV_BYTES);
            System.arraycopy(combined, GCM_IV_BYTES, ciphertext, 0, ciphertext.length);

            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] plaintext = cipher.doFinal(ciphertext);
            String token = new String(plaintext, StandardCharsets.UTF_8);
            if (token.trim().isEmpty()) {
                wipeStoredState();
                result.put("token", JSObject.NULL);
            } else {
                result.put("token", token);
            }
            call.resolve(result);
        } catch (Exception error) {
            // Key invalidated/lost or ciphertext corrupted: wipe both and force clean sign-in.
            wipeStoredState();
            result.put("token", JSObject.NULL);
            call.resolve(result);
        }
    }

    @PluginMethod
    public void clear(PluginCall call) {
        wipeStoredState();
        call.resolve();
    }

    @PluginMethod
    public void getDeviceLabel(PluginCall call) {
        String raw = Build.MODEL != null ? Build.MODEL.trim() : "";
        if (raw.isEmpty()) {
            raw = "Android device";
        }
        if (raw.length() > MAX_DEVICE_LABEL_LENGTH) {
            raw = raw.substring(0, MAX_DEVICE_LABEL_LENGTH).trim();
        }
        JSObject result = new JSObject();
        result.put("label", raw.isEmpty() ? "Android device" : raw);
        call.resolve(result);
    }
}
