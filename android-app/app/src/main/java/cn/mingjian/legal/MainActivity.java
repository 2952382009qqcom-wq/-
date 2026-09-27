package cn.mingjian.legal;

import android.Manifest;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import androidx.core.content.FileProvider;

import com.google.firebase.FirebaseApp;
import com.google.firebase.messaging.FirebaseMessaging;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;


public final class MainActivity extends ComponentActivity {
    private static final int FILE_CHOOSER_REQUEST = 901;
    private static final String TRUSTED_HOST = "39.96.14.33";

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorView;
    private ValueCallback<Uri[]> pendingFileCallback;
    private Uri cameraOutputUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(107, 53, 48));
        getWindow().setNavigationBarColor(Color.rgb(107, 53, 48));

        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(3)
        );
        progressParams.gravity = Gravity.TOP;
        root.addView(progressBar, progressParams);

        errorView = createErrorView();
        root.addView(errorView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        setContentView(root);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 902);
        }
        configureWebView();
        configureBackNavigation();

        if (savedInstanceState == null || webView.restoreState(savedInstanceState) == null) {
            webView.loadUrl(notificationUrl(getIntent()));
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        webView.loadUrl(notificationUrl(intent));
    }

    private String notificationUrl(Intent intent) {
        String route = intent == null ? null : intent.getStringExtra("notification_route");
        if (route == null || !route.startsWith("/") || route.startsWith("//")) {
            return BuildConfig.APP_URL;
        }
        return BuildConfig.APP_URL.replaceAll("/$", "") + route;
    }

    private void configureBackNavigation() {
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (errorView.getVisibility() == View.VISIBLE) {
                    errorView.setVisibility(View.GONE);
                    webView.loadUrl(BuildConfig.APP_URL);
                } else if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    setEnabled(false);
                    getOnBackPressedDispatcher().onBackPressed();
                }
            }
        });
    }

    @SuppressWarnings("SetJavaScriptEnabled")
    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setUserAgentString(settings.getUserAgentString() + " MingJianAndroid/1.0");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            settings.setSafeBrowsingEnabled(true);
        }

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                errorView.setVisibility(View.GONE);
                progressBar.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                CookieManager.getInstance().flush();
                registerPushTokenWithWebSession();
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return openExternalIfNeeded(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return openExternalIfNeeded(Uri.parse(url));
            }

            @Override
            public void onReceivedError(
                    WebView view,
                    WebResourceRequest request,
                    WebResourceError error
            ) {
                if (request.isForMainFrame()) {
                    showNetworkError();
                }
            }

        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onShowFileChooser(
                    WebView webView,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams
            ) {
                if (pendingFileCallback != null) {
                    pendingFileCallback.onReceiveValue(null);
                }
                pendingFileCallback = filePathCallback;
                launchFileChooser(fileChooserParams);
                return true;
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
            } catch (Exception exception) {
                Toast.makeText(this, "没有可处理该下载的应用", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void registerPushTokenWithWebSession() {
        if (FirebaseApp.getApps(this).isEmpty()) {
            return;
        }
        FirebaseMessaging.getInstance().getToken().addOnSuccessListener(token -> {
            String quoted = org.json.JSONObject.quote(token);
            String script = "fetch('/api/notifications/devices',{method:'POST',credentials:'same-origin'," +
                    "headers:{'Content-Type':'application/json'},body:JSON.stringify({platform:'android',token:" + quoted + "})})";
            webView.evaluateJavascript(script, null);
        });
    }

    private boolean openExternalIfNeeded(Uri uri) {
        String scheme = uri.getScheme();
        String host = uri.getHost();
        if (("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))
                && TRUSTED_HOST.equalsIgnoreCase(host)) {
            return false;
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception exception) {
            Toast.makeText(this, "无法打开外部链接", Toast.LENGTH_SHORT).show();
        }
        return true;
    }

    private void launchFileChooser(WebChromeClient.FileChooserParams params) {
        Intent cameraIntent = createCameraIntent();
        boolean imageCaptureRequested = params.isCaptureEnabled() && acceptsImages(params.getAcceptTypes());

        try {
            if (imageCaptureRequested && cameraIntent != null) {
                startActivityForResult(cameraIntent, FILE_CHOOSER_REQUEST);
                return;
            }

            Intent contentIntent = params.createIntent();
            contentIntent.addCategory(Intent.CATEGORY_OPENABLE);
            Intent chooser = Intent.createChooser(contentIntent, "选择文件或拍照");
            if (cameraIntent != null && acceptsImages(params.getAcceptTypes())) {
                chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{cameraIntent});
            }
            startActivityForResult(chooser, FILE_CHOOSER_REQUEST);
        } catch (Exception exception) {
            finishFileSelection(null);
            Toast.makeText(this, "无法启动相机或文件选择器", Toast.LENGTH_LONG).show();
        }
    }

    private Intent createCameraIntent() {
        Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (intent.resolveActivity(getPackageManager()) == null) {
            return null;
        }
        try {
            File directory = new File(getCacheDir(), "camera");
            if (!directory.exists() && !directory.mkdirs()) {
                return null;
            }
            File photo = File.createTempFile("mingjian_", ".jpg", directory);
            cameraOutputUri = FileProvider.getUriForFile(
                    this,
                    getPackageName() + ".fileprovider",
                    photo
            );
            intent.putExtra(MediaStore.EXTRA_OUTPUT, cameraOutputUri);
            intent.setClipData(ClipData.newRawUri("明鉴拍照材料", cameraOutputUri));
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            return intent;
        } catch (IOException exception) {
            cameraOutputUri = null;
            return null;
        }
    }

    private boolean acceptsImages(String[] acceptTypes) {
        if (acceptTypes == null || acceptTypes.length == 0) {
            return true;
        }
        for (String acceptType : acceptTypes) {
            if (acceptType == null || acceptType.trim().isEmpty() || acceptType.startsWith("image/")) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER_REQUEST) {
            return;
        }

        Uri[] results = null;
        if (resultCode == RESULT_OK) {
            if (data != null && data.getClipData() != null) {
                ClipData clipData = data.getClipData();
                List<Uri> uris = new ArrayList<>();
                for (int index = 0; index < clipData.getItemCount(); index++) {
                    uris.add(clipData.getItemAt(index).getUri());
                }
                results = uris.toArray(new Uri[0]);
            } else if (data != null && data.getData() != null) {
                results = new Uri[]{data.getData()};
            } else if (cameraOutputUri != null) {
                results = new Uri[]{cameraOutputUri};
            }
        }
        finishFileSelection(results);
    }

    private void finishFileSelection(Uri[] results) {
        if (pendingFileCallback != null) {
            pendingFileCallback.onReceiveValue(results);
            pendingFileCallback = null;
        }
        cameraOutputUri = null;
    }

    private LinearLayout createErrorView() {
        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setGravity(Gravity.CENTER);
        container.setPadding(dp(32), dp(32), dp(32), dp(32));
        container.setBackgroundColor(Color.rgb(250, 247, 242));
        container.setVisibility(View.GONE);

        TextView title = new TextView(this);
        title.setText("暂时无法连接明鉴");
        title.setTextSize(21);
        title.setTextColor(Color.rgb(62, 47, 46));
        title.setGravity(Gravity.CENTER);
        container.addView(title);

        TextView description = new TextView(this);
        description.setText("请检查网络连接后重试。法律分析服务需要连接公网服务器。");
        description.setTextSize(14);
        description.setTextColor(Color.rgb(94, 90, 82));
        description.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams descriptionParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        descriptionParams.setMargins(0, dp(12), 0, dp(20));
        container.addView(description, descriptionParams);

        Button retry = new Button(this);
        retry.setText("重新连接");
        retry.setTextColor(Color.WHITE);
        retry.setBackgroundColor(Color.rgb(140, 78, 71));
        retry.setOnClickListener(view -> {
            errorView.setVisibility(View.GONE);
            webView.loadUrl(BuildConfig.APP_URL);
        });
        container.addView(retry, new LinearLayout.LayoutParams(dp(160), dp(48)));
        return container;
    }

    private void showNetworkError() {
        progressBar.setVisibility(View.GONE);
        errorView.setVisibility(View.VISIBLE);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onDestroy() {
        if (pendingFileCallback != null) {
            pendingFileCallback.onReceiveValue(null);
            pendingFileCallback = null;
        }
        webView.stopLoading();
        webView.setWebChromeClient(null);
        webView.setWebViewClient(null);
        webView.destroy();
        super.onDestroy();
    }
}
