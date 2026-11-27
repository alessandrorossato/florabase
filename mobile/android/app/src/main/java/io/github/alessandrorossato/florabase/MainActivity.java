package io.github.alessandrorossato.florabase;

import android.os.Bundle;
import android.webkit.WebSettings;
import com.getcapacitor.BridgeActivity;
import java.io.File;

public class MainActivity extends BridgeActivity {

    private static void deleteRecursively(File target) {
        if (target == null || !target.exists()) {
            return;
        }
        File[] children = target.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursively(child);
            }
        }
        // Best-effort cleanup of ephemeral shared cache files.
        target.delete();
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Delete any previously exported/shared files in cache/shared/ on app start.
        deleteRecursively(new File(getCacheDir(), "shared"));

        registerPlugin(SecureTokenPlugin.class);
        registerPlugin(WebPrintPlugin.class);
        super.onCreate(savedInstanceState);

        // Debug builds only: permit mixed-content fetch() from the bundled https://localhost
        // WebView to local HTTP dev servers (e.g. http://10.0.2.2:5173). Release builds always
        // enforce allowMixedContent=false (capacitor.config.ts) and cleartextTrafficPermitted=false
        // (src/main/res/xml/network_security_config.xml).
        if (BuildConfig.DEBUG && getBridge() != null && getBridge().getWebView() != null) {
            getBridge()
                .getWebView()
                .getSettings()
                .setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }
    }
}
