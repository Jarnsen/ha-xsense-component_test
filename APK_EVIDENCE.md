# X-Sense APK Evidence

X-Sense APK reverse-engineering evidence for this integration belongs in:

`references/xsense_apk/`

Use that folder for recovered APK/XAPK files, jadx output, and short evidence notes. Do not rely on `.tmp`, OS temp folders, or disposable Codex work folders for APK evidence.

The local checkout currently excludes `references/` because that folder can contain large research material. If APK evidence notes need to ship in the repo, add the small note files explicitly or mirror the decision in this tracked file.

Before changing APK-sensitive behavior, recover or refresh the APK evidence and compare the implementation against it. APK-sensitive behavior includes camera events, recording playback, AI notifications, WebRTC signaling, and alarm-topic mappings.
