package {{PACKAGE_NAME}};

import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

public class DevicePlugin extends H2APlugin {

    @Override
    public boolean execute(String action, JSONArray args, String callbackId) throws Exception {
        if ("getInfo".equals(action)) {
            JSONObject info = new JSONObject();
            info.put("platform",     "Android");
            info.put("version",      Build.VERSION.RELEASE);
            info.put("sdk",          Build.VERSION.SDK_INT);
            info.put("model",        Build.MODEL);
            info.put("manufacturer", Build.MANUFACTURER);
            info.put("brand",        Build.BRAND);
            info.put("product",      Build.PRODUCT);
            bridge.sendResult(callbackId, info.toString(), false);
            return true;
        }
        return false;
    }
}
