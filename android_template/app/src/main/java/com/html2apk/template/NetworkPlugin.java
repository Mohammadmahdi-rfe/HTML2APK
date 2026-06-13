package {{PACKAGE_NAME}};

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import org.json.JSONArray;

@SuppressWarnings("deprecation")
public class NetworkPlugin extends H2APlugin {

    @Override
    public boolean execute(String action, JSONArray args, String callbackId) throws Exception {
        ConnectivityManager cm =
            (ConnectivityManager) activity.getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo info = cm != null ? cm.getActiveNetworkInfo() : null;
        boolean connected = info != null && info.isConnected();

        if ("isOnline".equals(action)) {
            bridge.sendResult(callbackId, String.valueOf(connected), false);
            return true;
        }
        if ("getConnectionType".equals(action)) {
            String type = "none";
            if (connected) {
                int t = info.getType();
                if (t == ConnectivityManager.TYPE_WIFI)   type = "wifi";
                else if (t == ConnectivityManager.TYPE_MOBILE) type = "cellular";
                else type = "other";
            }
            bridge.sendResult(callbackId, "\"" + type + "\"", false);
            return true;
        }
        return false;
    }
}
