package io.github.alessandrorossato.florabase;

import android.content.Context;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.WebView;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Exposes Android's built-in PrintManager for WebView pages (used by Florabase's
 * Labels screen where window.print() is otherwise a no-op inside Android WebView).
 * Uses only AOSP android.print APIs (zero third-party or Play Services dependencies).
 */
@CapacitorPlugin(name = "WebPrint")
public class WebPrintPlugin extends Plugin {

    @PluginMethod
    public void print(PluginCall call) {
        final String requested = call.getString("jobName");
        final String jobName =
            (requested != null && !requested.trim().isEmpty())
                ? requested.trim()
                : "Florabase Labels";

        if (getActivity() == null || getBridge() == null || getBridge().getWebView() == null) {
            call.reject("Printing is unavailable right now.");
            return;
        }

        getActivity().runOnUiThread(() -> {
            try {
                PrintManager printManager = (PrintManager) getActivity()
                    .getSystemService(Context.PRINT_SERVICE);
                WebView webView = getBridge().getWebView();
                if (printManager == null || webView == null) {
                    call.reject("Android print service is unavailable on this device.");
                    return;
                }
                PrintDocumentAdapter adapter = webView.createPrintDocumentAdapter(jobName);
                printManager.print(jobName, adapter, new PrintAttributes.Builder().build());
                call.resolve();
            } catch (Exception error) {
                call.reject("Could not start Android print job.");
            }
        });
    }
}
