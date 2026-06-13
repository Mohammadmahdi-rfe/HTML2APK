package {{PACKAGE_NAME}};

import android.app.Activity;
import android.content.Intent;
import org.json.JSONArray;

public abstract class H2APlugin {
    protected Activity activity;
    protected H2ABridge bridge;

    public void init(Activity activity, H2ABridge bridge) {
        this.activity = activity;
        this.bridge = bridge;
    }

    public abstract boolean execute(String action, JSONArray args, String callbackId) throws Exception;

    public void onActivityResult(int requestCode, int resultCode, Intent data) {}
}
