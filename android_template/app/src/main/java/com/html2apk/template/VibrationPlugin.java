package {{PACKAGE_NAME}};

import android.content.Context;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import org.json.JSONArray;

public class VibrationPlugin extends H2APlugin {

    @Override
    @SuppressWarnings("deprecation")
    public boolean execute(String action, JSONArray args, String callbackId) throws Exception {
        if ("vibrate".equals(action)) {
            long ms = args.length() > 0 ? args.getLong(0) : 500;
            Vibrator v = (Vibrator) activity.getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null && v.hasVibrator()) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    v.vibrate(ms);
                }
            }
            bridge.sendResult(callbackId, "null", false);
            return true;
        }
        return false;
    }
}
