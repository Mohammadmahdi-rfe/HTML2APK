package {{PACKAGE_NAME}};

import android.app.Activity;
import android.content.Intent;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import org.json.JSONArray;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class H2ABridge {
    private final Activity activity;
    private final WebView webView;
    private final Map<String, H2APlugin> plugins = new HashMap<>();
    private final List<H2APlugin> pluginList = new ArrayList<>();

    public H2ABridge(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
        registerBuiltinPlugins();
    }

    private void registerBuiltinPlugins() {
        addPlugin("Device",    new DevicePlugin());
        addPlugin("Vibration", new VibrationPlugin());
        addPlugin("Toast",     new ToastPlugin());
        addPlugin("Network",   new NetworkPlugin());
        addPlugin("Clipboard", new ClipboardPlugin());
    }

    public void addPlugin(String name, H2APlugin plugin) {
        plugin.init(activity, this);
        plugins.put(name, plugin);
        pluginList.add(plugin);
    }

    @JavascriptInterface
    public void exec(String service, String action, String argsJson, String callbackId) {
        try {
            JSONArray args = (argsJson != null && !argsJson.isEmpty())
                ? new JSONArray(argsJson) : new JSONArray();
            H2APlugin plugin = plugins.get(service);
            if (plugin == null) {
                sendError(callbackId, "Plugin not found: " + service);
                return;
            }
            boolean handled = plugin.execute(action, args, callbackId);
            if (!handled) sendError(callbackId, "Action not handled: " + action);
        } catch (Exception e) {
            sendError(callbackId, e.getMessage() != null ? e.getMessage() : "Unknown error");
        }
    }

    public void sendResult(final String callbackId, final String resultJson, final boolean keepCallback) {
        final String js = "if(window.html2apk)html2apk._callbackSuccess('"
            + escJs(callbackId) + "'," + resultJson + "," + keepCallback + ")";
        activity.runOnUiThread(() -> webView.evaluateJavascript(js, null));
    }

    public void sendError(final String callbackId, final String error) {
        final String js = "if(window.html2apk)html2apk._callbackError('"
            + escJs(callbackId) + "','" + escJs(error) + "')";
        activity.runOnUiThread(() -> webView.evaluateJavascript(js, null));
    }

    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        for (H2APlugin p : pluginList) p.onActivityResult(requestCode, resultCode, data);
    }

    private String escJs(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("'", "\\'")
                .replace("\n", "\\n").replace("\r", "");
    }

    public Activity getActivity() { return activity; }
    public WebView getWebView()   { return webView;   }
}
