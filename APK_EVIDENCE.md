# X-Sense APK Evidence

X-Sense APK reverse-engineering evidence for this integration belongs in:

`references/xsense_apk/`

Use that folder for recovered APK/XAPK files, jadx output, and short evidence notes. Do not rely on `.tmp`, OS temp folders, or disposable Codex work folders for APK evidence.

The local checkout currently excludes `references/` because that folder can contain large research material. If APK evidence notes need to ship in the repo, add the small note files explicitly or mirror the decision in this tracked file.

Before changing APK-sensitive behavior, recover or refresh the APK evidence and compare the implementation against it. APK-sensitive behavior includes camera events, recording playback, AI notifications, WebRTC signaling, and alarm-topic mappings.

Current local APK evidence:

- X-Sense APK `v1.40.0_20260612`, app code `1400`, package `com.xsense.security`, is stored locally as `references/xsense_apk/original/xsense-1400.apk`.
- Decompiled JADX output for app code `1400` is stored locally under `references/xsense_apk/decompiled/1400/`.
- `resources/AndroidManifest.xml` confirms `android:versionCode="1400"` and `android:versionName="v1.40.0_20260612"`.
- `sources/j2/C3839E.java` confirms signed API payload metadata: `appCode=1400`, `appVersion=v1.40.0_20260612`, `clientType=2`.
- `sources/A3/C1233g.java` confirms the decoded Cognito client secret strips the app-code prefix using `String.valueOf(1400).length()`.
- `sources/Q/v.java` confirms the ADDX/VicoHome camera metadata remains `VicoHome`, `com.ai.vicoo`, version code `200700500`, version name `2.7.5`.
- `sources/V1/f.java` is the primary APK device-type helper. At review time, a mechanical comparison of its model strings against `custom_components/xsense/python_xsense/entity_map.py` reported no missing APK helper models. Re-run that comparison whenever the APK is refreshed.
