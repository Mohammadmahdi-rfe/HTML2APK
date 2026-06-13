package {{PACKAGE_NAME}};

import android.widget.Toast;
import org.json.JSONArray;

public class ToastPlugin extends H2APlugin {

    @Override
    public boolean execute(String action, JSONArray args, String callbackId) throws Exception {
        if ("show".equals(action)) {
            String message = args.getString(0);
            boolean isLong = args.length() > 1 && "long".equalsIgnoreCase(args.getString(1));
            int dur = isLong ? Toast.LENGTH_LONG : Toast.LENGTH_SHORT;
            activity.runOnUiThread(() -> Toast.makeText(activity, message, dur).show());
            bridge.sendResult(callbackId, "null", false);
            return true;
        }
        return false;
    }
}
