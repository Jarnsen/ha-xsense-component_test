## 🎥 v.1.2.6.4

A camera playback and login reliability polish release. This version tightens the camera/WebRTC path against the Android app behavior and makes initial X-Sense login failures fail cleanly instead of hanging behind a broad Home Assistant timeout.

### ✨ Highlights

- 🎥 Adds the X-Sense/ADDX WebRTC signaling bridge used by the Android app camera player.
- 💤 Sends the APK live-view `verifyDormancyStatus` flag when requesting WebRTC camera tickets.
- 🧭 Uses the APK `auto` live-resolution fallback when no saved camera live ratio is available.
- ⚙️ Loads camera form options from the same ADDX settings endpoint the app uses.
- ⏱️ Aligns Cognito login network bounds with the AWS Android SDK defaults used by the app.

### 🛠️ Fixed

- Fixed WebRTC cameras being exposed to Home Assistant stream handling without the ADDX signal bridge they require.
- Fixed camera ticket requests missing the normal APK live-view dormancy verification flag.
- Fixed stale camera cleanup when the ADDX camera list is valid but empty.
- Fixed login attempts waiting too long or surfacing poorly when Cognito cannot be reached.
- Fixed camera motion sensitivity controls when the settings response omits the option list.
