package io.github.alessandrorossato.florabase;

import android.os.Bundle;
import android.webkit.WebSettings;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SecureTokenPlugin.class);
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
