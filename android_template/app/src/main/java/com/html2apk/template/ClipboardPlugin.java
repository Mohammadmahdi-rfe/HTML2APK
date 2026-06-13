package {{PACKAGE_NAME}};

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import org.json.JSONArray;

public class ClipboardPlugin extends H2APlugin {

    @Override
    public boolean execute(String action, JSONArray args, String callbackId) throws Exception {
        ClipboardManager cm =
            (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);

        if ("copy".equals(action) && cm != null) {
            String text = args.getString(0);
            activity.runOnUiThread(() ->
                cm.setPrimaryClip(ClipData.newPlainText("text", text)));
            bridge.sendResult(callbackId, "null", false);
            return true;
        }

        if ("paste".equals(action) && cm != null) {
            ClipData data = cm.getPrimaryClip();
            String text = "";
            if (data != null && data.getItemCount() > 0) {
                CharSequence seq = data.getItemAt(0).coerceToText(activity);
                if (seq != null) text = seq.toString();
            }
            bridge.sendResult(callbackId, "\"" + escJson(text) + "\"", false);
            return true;
        }
        return false;
    }

    private String escJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "");
    }
}
