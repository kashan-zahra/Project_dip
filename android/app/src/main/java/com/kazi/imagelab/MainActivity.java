package com.kazi.imagelab;

import android.Manifest;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Image Lab for Android.
 * Shows the same web app (the "web" folder) inside a WebView.
 * All image processing runs on the phone with OpenCV.js - no internet needed.
 */
public class MainActivity extends Activity {

    private static final int PICK_IMAGE = 1;
    private static final int ASK_STORAGE = 2;
    private static final int TAKE_PHOTO = 3;
    // the web files are served from this address, so they behave like a normal website
    private static final String START_URL = "https://appassets.androidplatform.net/assets/index.html";

    private WebView web;
    private ValueCallback<Uri[]> pendingChooser;
    private String pendingSave;
    private String cameraFile;      // where the camera app writes the photo (survives restarts)
    private boolean pageReady;
    private String pendingJs;       // photo waiting for the page to finish loading

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState != null) cameraFile = savedInstanceState.getString("cameraFile");

        // lets you inspect the app from your PC: open chrome://inspect in Chrome
        WebView.setWebContentsDebuggingEnabled(true);

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#F4F6F8"));
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);

        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return loader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                pageReady = true;
                if (pendingJs != null) {
                    String js = pendingJs;
                    pendingJs = null;
                    web.evaluateJavascript(js, null);
                }
            }
        });

        // "choose an image" buttons open the phone's gallery / file picker
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (pendingChooser != null) pendingChooser.onReceiveValue(null);
                pendingChooser = callback;
                Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("image/*");
                pick.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                try {
                    startActivityForResult(Intent.createChooser(pick, "Choose an image"), PICK_IMAGE);
                } catch (Exception e) {
                    pendingChooser = null;
                    return false;
                }
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "AndroidBridge");

        web.loadUrl(START_URL);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == TAKE_PHOTO) {
            final String path = cameraFile;
            cameraFile = null;
            if (resultCode != RESULT_OK || path == null) return;          // user cancelled
            // shrink + rotate the photo off the main thread, then hand it to the page
            new Thread(() -> {
                String dataUrl = photoToDataUrl(path);
                String js = dataUrl == null
                        ? "window.onImageSaved && window.onImageSaved(false, 'Could not read the photo.')"
                        : "window.openImageFromApp && window.openImageFromApp('" + dataUrl + "')";
                runOnUiThread(() -> runWhenReady(js));
            }).start();
            return;
        }
        if (requestCode == PICK_IMAGE && pendingChooser != null) {
            Uri[] result = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
            if (result == null && resultCode == RESULT_OK && data != null && data.getData() != null) {
                result = new Uri[]{data.getData()};
            }
            pendingChooser.onReceiveValue(result);
            pendingChooser = null;
        }
    }

    private void runWhenReady(String js) {
        if (pageReady) web.evaluateJavascript(js, null);
        else pendingJs = js;           // the app was restarted: wait for the page
    }

    /** Start the phone's camera app; the photo is written to our cache folder. */
    private void openCamera() {
        try {
            File dir = new File(getCacheDir(), "camera");
            if (!dir.exists()) dir.mkdirs();
            File[] old = dir.listFiles();                  // keep only the newest photo
            if (old != null) for (File f : old) f.delete();
            File photo = new File(dir, "photo_" + System.currentTimeMillis() + ".jpg");
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".files", photo);
            Intent cam = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            cam.putExtra(MediaStore.EXTRA_OUTPUT, uri);
            cam.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            cameraFile = photo.getAbsolutePath();
            startActivityForResult(cam, TAKE_PHOTO);
        } catch (Exception e) {
            cameraFile = null;
            tellWeb(false, "No camera app found on this phone.");
        }
    }

    /** Load the photo at most 1000 px (like app.py), turned the right way up, as a JPEG data URL. */
    private String photoToDataUrl(String path) {
        try {
            File f = new File(path);
            if (!f.exists() || f.length() == 0) return null;
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(path, o);
            int sample = 1;
            while (Math.max(o.outWidth, o.outHeight) / (sample * 2) >= 1000) sample *= 2;
            o = new BitmapFactory.Options();
            o.inSampleSize = sample;
            Bitmap bmp = BitmapFactory.decodeFile(path, o);
            if (bmp == null) return null;

            float scale = Math.min(1f, 1000f / Math.max(bmp.getWidth(), bmp.getHeight()));
            Matrix m = new Matrix();
            m.postScale(scale, scale);
            int orient = new ExifInterface(path).getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            if (orient == ExifInterface.ORIENTATION_ROTATE_90) m.postRotate(90);
            else if (orient == ExifInterface.ORIENTATION_ROTATE_180) m.postRotate(180);
            else if (orient == ExifInterface.ORIENTATION_ROTATE_270) m.postRotate(270);
            Bitmap out = Bitmap.createBitmap(bmp, 0, 0, bmp.getWidth(), bmp.getHeight(), m, true);

            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            out.compress(Bitmap.CompressFormat.JPEG, 95, buf);
            f.delete();
            return "data:image/jpeg;base64," + Base64.encodeToString(buf.toByteArray(), Base64.NO_WRAP);
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putString("cameraFile", cameraFile);
    }

    @Override
    public void onBackPressed() {
        // if the user is on the "Lab Data" page, go back to the Studio first
        // the page decides: close the guide, leave Lab Data, go back from a tool to its group...
        web.evaluateJavascript(
                "(function(){return window.appBack ? appBack() : false;})()",
                value -> {
                    if (!"true".equals(value)) MainActivity.super.onBackPressed();
                });
    }

    // ---------------- saving the result picture ----------------

    /** Called from JavaScript: window.AndroidBridge.saveImage(dataUrl) */
    private class Bridge {
        @JavascriptInterface
        public void takePhoto() {
            runOnUiThread(MainActivity.this::openCamera);
        }

        @JavascriptInterface
        public void saveImage(String dataUrl) {
            runOnUiThread(() -> {
                if (Build.VERSION.SDK_INT < 29 && checkSelfPermission(
                        Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                    pendingSave = dataUrl;
                    requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, ASK_STORAGE);
                    return;
                }
                save(dataUrl);
            });
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == ASK_STORAGE && pendingSave != null) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) save(pendingSave);
            else tellWeb(false, "Permission needed to save into the gallery.");
            pendingSave = null;
        }
    }

    private void save(String dataUrl) {
        try {
            byte[] png = Base64.decode(dataUrl.substring(dataUrl.indexOf(',') + 1), Base64.DEFAULT);
            String name = "ImageLab_" + new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
                    .format(new Date()) + ".png";

            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.Images.Media.DISPLAY_NAME, name);
                v.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
                v.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Image Lab");
                Uri uri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v);
                if (uri == null) throw new Exception("no gallery");
                try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                    out.write(png);
                }
            } else {
                File dir = new File(Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_PICTURES), "Image Lab");
                if (!dir.exists()) dir.mkdirs();
                File f = new File(dir, name);
                try (FileOutputStream out = new FileOutputStream(f)) {
                    out.write(png);
                }
                MediaScannerConnection.scanFile(this, new String[]{f.getAbsolutePath()}, null, null);
            }
            tellWeb(true, "Saved to your gallery (Pictures/Image Lab).");
        } catch (Exception e) {
            tellWeb(false, "Could not save the image.");
        }
    }

    private void tellWeb(boolean ok, String msg) {
        String js = "window.onImageSaved && window.onImageSaved(" + ok + ", " +
                org.json.JSONObject.quote(msg) + ")";
        web.post(() -> web.evaluateJavascript(js, null));
    }
}
