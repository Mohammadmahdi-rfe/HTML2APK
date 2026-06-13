package {{PACKAGE_NAME}};

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.view.Window;
import android.view.WindowManager;
import java.io.InputStream;

public class MainActivity extends Activity {

    private WebView webView;
    private H2ABridge bridge;
    private String bridgeJs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // {{FULLSCREEN_CODE}}

        webView = new WebView(this);
        setContentView(webView);

        bridge = new H2ABridge(this, webView);
        webView.addJavascriptInterface(bridge, "_H2ABridge");

        bridgeJs = loadAsset("www/html2apk.js");

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled({{JS_ENABLED}});
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setSupportZoom({{ZOOM_ENABLED}});
        s.setBuiltInZoomControls({{ZOOM_ENABLED}});
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMediaPlaybackRequiresUserGesture(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                view.loadUrl(url);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (bridgeJs != null) {
                    view.evaluateJavascript(bridgeJs, null);
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient());
        webView.loadUrl("file:///android_asset/www/index.html");
    }

    private String loadAsset(String path) {
        try {
            InputStream is = getAssets().open(path);
            byte[] buf = new byte[is.available()];
            is.read(buf);
            is.close();
            return new String(buf, "UTF-8");
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (bridge != null) bridge.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onPause()  { super.onPause();  webView.onPause();  }

    @Override
    protected void onResume() { super.onResume(); webView.onResume(); }
}
