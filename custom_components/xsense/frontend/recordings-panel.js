const HLS_JS_URL = "/xsense_recordings_static/vendor/hls.light.min.js";

const TRANSLATIONS = {
  "en": {
    allCamerasOffline: "All cameras offline",
    allCamerasOnline: "All cameras online",
    allCaughtUp: "All caught up",
    back: "Back",
    backgroundSyncControlsVisibility: "Background sync controls visibility",
    cached: "Cached",
    camera: "Camera",
    camerasOnline: "Cameras Online",
    genericCamera: "Camera",
    hlsPlaybackFailed: "HLS playback failed",
    hlsPlaybackUnsupported: "HLS playback is not supported by this browser",
    lazyCacheOnPlayback: "Lazy cache on playback",
    loading: "Loading",
    loadingRecordings: "Loading recordings...",
    newestRecording: "Newest Recording",
    noCameraSelected: "No camera selected",
    noCamerasFound: "No cameras found",
    noCamerasFoundSentence: "No cameras found.",
    noRecordingsForDate: "No recordings for this date.",
    noRecordingsReady: "No recordings ready",
    noThumbnail: "No thumbnail",
    noneYet: "None yet",
    notCached: "Not cached",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Preparing",
    preparingRecording: "Preparing recording...",
    ready: "Ready",
    readyToWatch: "Ready To Watch",
    recordingEmpty: "Recording is empty",
    recordingIsNotReady: "Recording is not ready yet.",
    recordingIsNotReadyStatus: "Recording is not ready ({status})",
    recordingsCountStatus: "{shown} of {total} recordings - {state}",
    recordingsReady: "Recordings are ready",
    refresh: "Refresh",
    selectRecordingToPlay: "Select a recording to play",
    storageUsed: "Storage Used",
    stillSyncing: "{count} still syncing",
    couldNotLoadHlsPlayer: "Could not load HLS player",
    date: "Date",
  },
  "as": {
    allCamerasOffline: "\u09b8\u0995\u09b2\u09cb \u0995\u09c7\u09ae\u09c7\u09f0\u09be \u0985\u09ab\u09b2\u09be\u0987\u09a8",
    allCamerasOnline: "\u09b8\u0995\u09b2\u09cb \u0995\u09c7\u09ae\u09c7\u09f0\u09be \u0985\u09a8\u09b2\u09be\u0987\u09a8",
    allCaughtUp: "\u09b8\u0995\u09b2\u09cb\u09f1\u09c7 \u09a7\u09f0\u09bf\u09b2\u09c7",
    back: "\u09aa\u09bf\u099b\u09b2\u09c8 \u0998\u09c2\u09f0\u09bf \u0986\u09b9\u09bf\u09b2",
    backgroundSyncControlsVisibility: "\u09aa\u099f\u09ad\u09c2\u09ae\u09bf \u099b\u09bf\u0999\u09cd\u0995\u09c7 \u09a6\u09c3\u09b6\u09cd\u09af\u09ae\u09be\u09a8\u09a4\u09be \u09a8\u09bf\u09af\u09bc\u09a8\u09cd\u09a4\u09cd\u09f0\u09a3 \u0995\u09f0\u09c7",
    cached: "\u0995\u09c7\u099a \u0995\u09f0\u09be \u09b9\u09c8\u099b\u09c7",
    camera: "\u0995\u09c7\u09ae\u09c7\u09f0\u09be",
    camerasOnline: "\u0995\u09c7\u09ae\u09c7\u09f0\u09be \u0985\u09a8\u09b2\u09be\u0987\u09a8",
    genericCamera: "\u0995\u09c7\u09ae\u09c7\u09f0\u09be",
    hlsPlaybackFailed: "HLS \u09aa\u09cd\u09b2\u09c7\u09ac\u09c7\u0995 \u09ac\u09bf\u09ab\u09b2",
    hlsPlaybackUnsupported: "\u098f\u0987 \u09ac\u09cd\u09f0\u09be\u0989\u099c\u09be\u09f0\u09c7 HLS \u09aa\u09cd\u09b2\u09c7\u09ac\u09c7\u0995 \u09b8\u09ae\u09f0\u09cd\u09a5\u09bf\u09a4 \u09a8\u09b9\u09af\u09bc",
    lazyCacheOnPlayback: "\u09aa\u09cd\u09b2\u09c7\u09ac\u09c7\u0995\u09a4 \u098f\u09b2\u09c7\u09b9\u09c1\u09f1\u09be \u0995\u09c7\u099a",
    loading: "\u09b2\u09cb\u09a1 \u09b9\u09c8 \u0986\u099b\u09c7",
    loadingRecordings: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09b2\u09cb\u09a1 \u0995\u09f0\u09bf \u0986\u099b\u09c7...",
    newestRecording: "\u09a8\u09a4\u09c1\u09a8 \u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982",
    noCameraSelected: "\u0995\u09cb\u09a8\u09cb \u0995\u09c7\u09ae\u09c7\u09f0\u09be \u09a8\u09bf\u09f0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u0995\u09f0\u09be \u09b9\u09cb\u09f1\u09be \u09a8\u09be\u0987",
    noCamerasFound: "\u0995\u09cb\u09a8\u09cb \u0995\u09c7\u09ae\u09c7\u09f0\u09be \u09aa\u09cb\u09f1\u09be \u09a8\u0997\u2019\u09b2",
    noCamerasFoundSentence: "\u0995\u09cb\u09a8\u09cb \u0995\u09c7\u09ae\u09c7\u09f0\u09be \u09aa\u09cb\u09f1\u09be \u09a8\u0997\u2019\u09b2\u0964",
    noRecordingsForDate: "\u098f\u0987 \u09a4\u09be\u09f0\u09bf\u0996\u09f0 \u09ac\u09be\u09ac\u09c7 \u0995\u09cb\u09a8\u09cb \u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09a8\u09be\u0987\u0964",
    noRecordingsReady: "\u0995\u09cb\u09a8\u09cb \u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09b8\u09be\u099c\u09c1 \u09a8\u09b9\u09af\u09bc",
    noThumbnail: "\u0995\u09cb\u09a8\u09cb \u09a5\u09be\u09ae\u09cd\u09ac\u09a8\u09c7\u0987\u09b2 \u09a8\u09be\u0987",
    noneYet: "\u098f\u09a4\u09bf\u09af\u09bc\u09be\u0993 \u0995\u09cb\u09a8\u09cb \u09a8\u09be\u0987",
    notCached: "\u0995\u09c7\u099a \u0995\u09f0\u09be \u09b9\u09cb\u09f1\u09be \u09a8\u09be\u0987",
    offline: "\u0985\u09ab\u09b2\u09be\u0987\u09a8",
    offlineCount: "{count} \u0985\u09ab\u09b2\u09be\u0987\u09a8",
    online: "\u0985\u09a8\u09b2\u09be\u0987\u09a8",
    preparing: "\u09aa\u09cd\u09f0\u09b8\u09cd\u09a4\u09c1\u09a4\u09bf \u099a\u09b2\u09be\u0987 \u0986\u099b\u09c7",
    preparingRecording: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09aa\u09cd\u09f0\u09b8\u09cd\u09a4\u09c1\u09a4 \u0995\u09f0\u09be \u09b9\u09c8\u099b\u09c7...",
    ready: "\u09f0\u09c7\u09a1\u09bf",
    readyToWatch: "\u09f0\u09c7\u09a1\u09bf \u099f\u09c1 \u09f1\u09be\u099a",
    recordingEmpty: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u0996\u09be\u09b2\u09c0 \u09b9\u09c8 \u0986\u099b\u09c7",
    recordingIsNotReady: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u098f\u09a4\u09bf\u09af\u09bc\u09be\u0993 \u09b8\u09be\u099c\u09c1 \u09b9\u09cb\u09f1\u09be \u09a8\u09be\u0987\u0964",
    recordingIsNotReadyStatus: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09aa\u09cd\u09f0\u09b8\u09cd\u09a4\u09c1\u09a4 \u09b9\u09cb\u09f1\u09be \u09a8\u09be\u0987 ({status})",
    recordingsCountStatus: "{total} \u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982\u09b8\u09ae\u09c2\u09b9\u09f0 {shown} - {state}",
    recordingsReady: "\u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09b8\u09be\u099c\u09c1 \u09b9\u09c8\u099b\u09c7",
    refresh: "\u09b8\u09a4\u09c7\u099c \u0995\u09f0\u0995",
    selectRecordingToPlay: "\u09ac\u099c\u09be\u09ac\u09b2\u09c8 \u098f\u099f\u09be \u09f0\u09c7\u0995\u09f0\u09cd\u09a1\u09bf\u0982 \u09a8\u09bf\u09f0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09f0\u0995",
    storageUsed: "\u09b8\u0982\u09f0\u0995\u09cd\u09b7\u09a3 \u09ac\u09cd\u09af\u09f1\u09b9\u09c3\u09a4",
    stillSyncing: "{count} \u098f\u09a4\u09bf\u09af\u09bc\u09be\u0993 \u099b\u09bf\u0999\u09cd\u0995 \u09b9\u09c8 \u0986\u099b\u09c7",
    couldNotLoadHlsPlayer: "HLS \u09aa\u09cd\u09b2\u09c7\u09af\u09bc\u09be\u09f0 \u09b2\u09cb\u09a1 \u0995\u09f0\u09bf\u09ac \u09aa\u09f0\u09be \u09a8\u0997'\u09b2",
    date: "\u09a4\u09be\u09f0\u09bf\u0996",
  },
  "ar": {
    allCamerasOffline: "\u062c\u0645\u064a\u0639 \u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627\u062a \u063a\u064a\u0631 \u0645\u062a\u0635\u0644\u0629 \u0628\u0627\u0644\u0625\u0646\u062a\u0631\u0646\u062a",
    allCamerasOnline: "\u062c\u0645\u064a\u0639 \u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627\u062a \u0639\u0644\u0649 \u0627\u0644\u0627\u0646\u062a\u0631\u0646\u062a",
    allCaughtUp: "\u062c\u0645\u064a\u0639 \u0627\u0644\u0645\u062d\u0627\u0635\u0631\u064a\u0646",
    back: "\u0627\u0644\u0639\u0648\u062f\u0629",
    backgroundSyncControlsVisibility: "\u062a\u062a\u062d\u0643\u0645 \u0645\u0632\u0627\u0645\u0646\u0629 \u0627\u0644\u062e\u0644\u0641\u064a\u0629 \u0641\u064a \u0627\u0644\u0631\u0624\u064a\u0629",
    cached: "\u0645\u062e\u0628\u0623\u0629",
    camera: "\u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627",
    camerasOnline: "\u0643\u0627\u0645\u064a\u0631\u0627\u062a \u0639\u0644\u0649 \u0627\u0644\u0627\u0646\u062a\u0631\u0646\u062a",
    genericCamera: "\u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627",
    hlsPlaybackFailed: "\u0641\u0634\u0644 \u062a\u0634\u063a\u064a\u0644 HLS",
    hlsPlaybackUnsupported: "\u062a\u0634\u063a\u064a\u0644 HLS \u063a\u064a\u0631 \u0645\u062f\u0639\u0648\u0645 \u0645\u0646 \u0642\u0628\u0644 \u0647\u0630\u0627 \u0627\u0644\u0645\u062a\u0635\u0641\u062d",
    lazyCacheOnPlayback: "\u0630\u0627\u0643\u0631\u0629 \u0627\u0644\u062a\u062e\u0632\u064a\u0646 \u0627\u0644\u0645\u0624\u0642\u062a \u0643\u0633\u0648\u0644 \u0639\u0646\u062f \u0627\u0644\u062a\u0634\u063a\u064a\u0644",
    loading: "\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644",
    loadingRecordings: "\u062c\u0627\u0631\u064d \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u062a\u0633\u062c\u064a\u0644\u0627\u062a...",
    newestRecording: "\u0623\u062d\u062f\u062b \u0627\u0644\u062a\u0633\u062c\u064a\u0644",
    noCameraSelected: "\u0644\u0645 \u064a\u062a\u0645 \u062a\u062d\u062f\u064a\u062f \u0623\u064a \u0643\u0627\u0645\u064a\u0631\u0627",
    noCamerasFound: "\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0643\u0627\u0645\u064a\u0631\u0627\u062a",
    noCamerasFoundSentence: "\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0643\u0627\u0645\u064a\u0631\u0627\u062a.",
    noRecordingsForDate: "\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0633\u062c\u064a\u0644\u0627\u062a \u0644\u0647\u0630\u0627 \u0627\u0644\u062a\u0627\u0631\u064a\u062e.",
    noRecordingsReady: "\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0633\u062c\u064a\u0644\u0627\u062a \u062c\u0627\u0647\u0632\u0629",
    noThumbnail: "\u0644\u0627 \u062a\u0648\u062c\u062f \u0635\u0648\u0631\u0629 \u0645\u0635\u063a\u0631\u0629",
    noneYet: "\u0644\u0627 \u0634\u064a\u0621 \u062d\u062a\u0649 \u0627\u0644\u0622\u0646",
    notCached: "\u063a\u064a\u0631 \u0645\u062e\u0628\u0623\u0629",
    offline: "\u063a\u064a\u0631 \u0645\u062a\u0635\u0644",
    offlineCount: "{count} \u063a\u064a\u0631 \u0645\u062a\u0635\u0644",
    online: "\u0639\u0644\u0649 \u0627\u0644\u0627\u0646\u062a\u0631\u0646\u062a",
    preparing: "\u062a\u062d\u0636\u064a\u0631",
    preparingRecording: "\u062c\u0627\u0631\u064d \u062a\u062d\u0636\u064a\u0631 \u0627\u0644\u062a\u0633\u062c\u064a\u0644...",
    ready: "\u062c\u0627\u0647\u0632",
    readyToWatch: "\u062c\u0627\u0647\u0632 \u0644\u0644\u0645\u0634\u0627\u0647\u062f\u0629",
    recordingEmpty: "\u0627\u0644\u062a\u0633\u062c\u064a\u0644 \u0641\u0627\u0631\u063a",
    recordingIsNotReady: "\u0627\u0644\u062a\u0633\u062c\u064a\u0644 \u0644\u064a\u0633 \u062c\u0627\u0647\u0632\u0627 \u0628\u0639\u062f.",
    recordingIsNotReadyStatus: "\u0627\u0644\u062a\u0633\u062c\u064a\u0644 \u063a\u064a\u0631 \u062c\u0627\u0647\u0632 ({status})",
    recordingsCountStatus: "{shown} \u0645\u0646 \u0625\u062c\u0645\u0627\u0644\u064a \u062a\u0633\u062c\u064a\u0644\u0627\u062a {total} - {state}",
    recordingsReady: "\u0627\u0644\u062a\u0633\u062c\u064a\u0644\u0627\u062a \u062c\u0627\u0647\u0632\u0629",
    refresh: "\u062a\u062d\u062f\u064a\u062b",
    selectRecordingToPlay: "\u062d\u062f\u062f \u062a\u0633\u062c\u064a\u0644\u0627\u064b \u0644\u062a\u0634\u063a\u064a\u0644\u0647",
    storageUsed: "\u0627\u0644\u062a\u062e\u0632\u064a\u0646 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u0629",
    stillSyncing: "\u0644\u0627 \u064a\u0632\u0627\u0644 {count} \u0642\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u0645\u0646\u0629",
    couldNotLoadHlsPlayer: "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0645\u0634\u063a\u0644 HLS",
    date: "\u0627\u0644\u062a\u0627\u0631\u064a\u062e",
  },
  "cs": {
    allCamerasOffline: "V\u0161echny kamery jsou offline",
    allCamerasOnline: "V\u0161echny kamery online",
    allCaughtUp: "V\u0161e dohn\u00e1no",
    back: "Zp\u011bt",
    backgroundSyncControlsVisibility: "Synchronizace na pozad\u00ed \u0159\u00edd\u00ed viditelnost",
    cached: "Ulo\u017eeno do mezipam\u011bti",
    camera: "Fotoapar\u00e1t",
    camerasOnline: "Kamery online",
    genericCamera: "Fotoapar\u00e1t",
    hlsPlaybackFailed: "P\u0159ehr\u00e1v\u00e1n\u00ed HLS se nezda\u0159ilo",
    hlsPlaybackUnsupported: "P\u0159ehr\u00e1v\u00e1n\u00ed HLS tento prohl\u00ed\u017ee\u010d nepodporuje",
    lazyCacheOnPlayback: "L\u00edn\u00e1 mezipam\u011b\u0165 p\u0159i p\u0159ehr\u00e1v\u00e1n\u00ed",
    loading: "Na\u010d\u00edt\u00e1n\u00ed",
    loadingRecordings: "Na\u010d\u00edt\u00e1n\u00ed nahr\u00e1vek...",
    newestRecording: "Nejnov\u011bj\u0161\u00ed nahr\u00e1vka",
    noCameraSelected: "Nen\u00ed vybr\u00e1na \u017e\u00e1dn\u00e1 kamera",
    noCamerasFound: "Nebyly nalezeny \u017e\u00e1dn\u00e9 kamery",
    noCamerasFoundSentence: "Nebyly nalezeny \u017e\u00e1dn\u00e9 kamery.",
    noRecordingsForDate: "Pro toto datum nejsou \u017e\u00e1dn\u00e9 nahr\u00e1vky.",
    noRecordingsReady: "Nejsou p\u0159ipraveny \u017e\u00e1dn\u00e9 nahr\u00e1vky",
    noThumbnail: "\u017d\u00e1dn\u00e1 miniatura",
    noneYet: "Zat\u00edm \u017e\u00e1dn\u00e9",
    notCached: "Nen\u00ed ulo\u017eeno v mezipam\u011bti",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "P\u0159\u00edprava",
    preparingRecording: "P\u0159\u00edprava nahr\u00e1v\u00e1n\u00ed...",
    ready: "P\u0159ipraveno",
    readyToWatch: "P\u0159ipraveno ke sledov\u00e1n\u00ed",
    recordingEmpty: "Z\u00e1znam je pr\u00e1zdn\u00fd",
    recordingIsNotReady: "Nahr\u00e1v\u00e1n\u00ed je\u0161t\u011b nen\u00ed p\u0159ipraveno.",
    recordingIsNotReadyStatus: "Nahr\u00e1v\u00e1n\u00ed nen\u00ed p\u0159ipraveno ({status})",
    recordingsCountStatus: "{shown} nahr\u00e1vek {total} - {state}",
    recordingsReady: "Nahr\u00e1vky jsou p\u0159ipraveny",
    refresh: "Obnovit",
    selectRecordingToPlay: "Vyberte nahr\u00e1vku, kterou chcete p\u0159ehr\u00e1t",
    storageUsed: "Pou\u017eit\u00e9 \u00falo\u017ei\u0161t\u011b",
    stillSyncing: "{count} se st\u00e1le synchronizuje",
    couldNotLoadHlsPlayer: "P\u0159ehr\u00e1va\u010d HLS nelze na\u010d\u00edst",
    date: "Datum",
  },
  "da": {
    allCamerasOffline: "Alle kameraer offline",
    allCamerasOnline: "Alle kameraer online",
    allCaughtUp: "Alle indhentet",
    back: "Tilbage",
    backgroundSyncControlsVisibility: "Baggrundssynkronisering styrer synlighed",
    cached: "Cachelagret",
    camera: "Kamera",
    camerasOnline: "Kameraer online",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS-afspilning mislykkedes",
    hlsPlaybackUnsupported: "HLS-afspilning underst\u00f8ttes ikke af denne browser",
    lazyCacheOnPlayback: "Lazy cache ved afspilning",
    loading: "Indl\u00e6ser",
    loadingRecordings: "Indl\u00e6ser optagelser...",
    newestRecording: "Nyeste optagelse",
    noCameraSelected: "Intet kamera valgt",
    noCamerasFound: "Ingen kameraer fundet",
    noCamerasFoundSentence: "Ingen kameraer fundet.",
    noRecordingsForDate: "Ingen optagelser for denne dato.",
    noRecordingsReady: "Ingen optagelser klar",
    noThumbnail: "Ingen thumbnail",
    noneYet: "Ingen endnu",
    notCached: "Ikke cachelagret",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Forbereder",
    preparingRecording: "Forbereder optagelse...",
    ready: "Klar",
    readyToWatch: "Klar til at se",
    recordingEmpty: "Optagelsen er tom",
    recordingIsNotReady: "Optagelsen er ikke klar endnu.",
    recordingIsNotReadyStatus: "Optagelsen er ikke klar ({status})",
    recordingsCountStatus: "{shown} af {total} optagelser - {state}",
    recordingsReady: "Optagelserne er klar",
    refresh: "Opdater",
    selectRecordingToPlay: "V\u00e6lg en optagelse, der skal afspilles",
    storageUsed: "Opbevaring brugt",
    stillSyncing: "{count} synkroniserer stadig",
    couldNotLoadHlsPlayer: "HLS-afspilleren kunne ikke indl\u00e6ses",
    date: "Dato",
  },
  "de": {
    allCamerasOffline: "Alle Kameras offline",
    allCamerasOnline: "Alle Kameras online",
    allCaughtUp: "Alles eingeholt",
    back: "Zur\u00fcck",
    backgroundSyncControlsVisibility: "Die Hintergrundsynchronisierung steuert die Sichtbarkeit",
    cached: "Zwischengespeichert",
    camera: "Kamera",
    camerasOnline: "Kameras online",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "Die HLS-Wiedergabe ist fehlgeschlagen",
    hlsPlaybackUnsupported: "Die HLS-Wiedergabe wird von diesem Browser nicht unterst\u00fctzt",
    lazyCacheOnPlayback: "Lazy Cache bei der Wiedergabe",
    loading: "Laden",
    loadingRecordings: "Aufnahmen werden geladen...",
    newestRecording: "Neueste Aufnahme",
    noCameraSelected: "Keine Kamera ausgew\u00e4hlt",
    noCamerasFound: "Keine Kameras gefunden",
    noCamerasFoundSentence: "Keine Kameras gefunden.",
    noRecordingsForDate: "F\u00fcr dieses Datum liegen keine Aufnahmen vor.",
    noRecordingsReady: "Keine Aufnahmen bereit",
    noThumbnail: "Kein Miniaturbild",
    noneYet: "Noch keine",
    notCached: "Nicht zwischengespeichert",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Vorbereiten",
    preparingRecording: "Aufnahme wird vorbereitet...",
    ready: "Bereit",
    readyToWatch: "Bereit zum Anschauen",
    recordingEmpty: "Die Aufnahme ist leer",
    recordingIsNotReady: "Die Aufnahme ist noch nicht fertig.",
    recordingIsNotReadyStatus: "Aufnahme ist nicht bereit ({status})",
    recordingsCountStatus: "{shown} von {total}-Aufnahmen - {state}",
    recordingsReady: "Die Aufnahmen sind fertig",
    refresh: "Aktualisieren",
    selectRecordingToPlay: "W\u00e4hlen Sie eine Aufnahme zum Abspielen aus",
    storageUsed: "Verwendeter Speicher",
    stillSyncing: "{count} wird noch synchronisiert",
    couldNotLoadHlsPlayer: "Der HLS-Player konnte nicht geladen werden",
    date: "Datum",
  },
  "el": {
    allCamerasOffline: "\u038c\u03bb\u03b5\u03c2 \u03bf\u03b9 \u03ba\u03ac\u03bc\u03b5\u03c1\u03b5\u03c2 \u03b5\u03ba\u03c4\u03cc\u03c2 \u03c3\u03cd\u03bd\u03b4\u03b5\u03c3\u03b7\u03c2",
    allCamerasOnline: "\u038c\u03bb\u03b5\u03c2 \u03bf\u03b9 \u03ba\u03ac\u03bc\u03b5\u03c1\u03b5\u03c2 online",
    allCaughtUp: "\u038c\u03bb\u03b1 \u03c0\u03b9\u03ac\u03c3\u03c4\u03b7\u03ba\u03b1\u03bd",
    back: "\u03a0\u03af\u03c3\u03c9",
    backgroundSyncControlsVisibility: "\u039f \u03c3\u03c5\u03b3\u03c7\u03c1\u03bf\u03bd\u03b9\u03c3\u03bc\u03cc\u03c2 \u03c6\u03cc\u03bd\u03c4\u03bf\u03c5 \u03b5\u03bb\u03ad\u03b3\u03c7\u03b5\u03b9 \u03c4\u03b7\u03bd \u03bf\u03c1\u03b1\u03c4\u03cc\u03c4\u03b7\u03c4\u03b1",
    cached: "\u0391\u03c0\u03bf\u03b8\u03b7\u03ba\u03b5\u03c5\u03bc\u03ad\u03bd\u03bf \u03c3\u03c4\u03b7\u03bd \u03ba\u03c1\u03c5\u03c6\u03ae \u03bc\u03bd\u03ae\u03bc\u03b7",
    camera: "\u039a\u03ac\u03bc\u03b5\u03c1\u03b1",
    camerasOnline: "\u039a\u03ac\u03bc\u03b5\u03c1\u03b5\u03c2 Online",
    genericCamera: "\u039a\u03ac\u03bc\u03b5\u03c1\u03b1",
    hlsPlaybackFailed: "\u0397 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae HLS \u03b1\u03c0\u03ad\u03c4\u03c5\u03c7\u03b5",
    hlsPlaybackUnsupported: "\u0397 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae HLS \u03b4\u03b5\u03bd \u03c5\u03c0\u03bf\u03c3\u03c4\u03b7\u03c1\u03af\u03b6\u03b5\u03c4\u03b1\u03b9 \u03b1\u03c0\u03cc \u03b1\u03c5\u03c4\u03cc \u03c4\u03bf \u03c0\u03c1\u03cc\u03b3\u03c1\u03b1\u03bc\u03bc\u03b1 \u03c0\u03b5\u03c1\u03b9\u03ae\u03b3\u03b7\u03c3\u03b7\u03c2",
    lazyCacheOnPlayback: "Lazy cache \u03ba\u03b1\u03c4\u03ac \u03c4\u03b7\u03bd \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae",
    loading: "\u03a6\u03cc\u03c1\u03c4\u03c9\u03c3\u03b7",
    loadingRecordings: "\u03a6\u03cc\u03c1\u03c4\u03c9\u03c3\u03b7 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ce\u03bd...",
    newestRecording: "\u039d\u03b5\u03cc\u03c4\u03b5\u03c1\u03b7 \u03b7\u03c7\u03bf\u03b3\u03c1\u03ac\u03c6\u03b7\u03c3\u03b7",
    noCameraSelected: "\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03b5\u03c0\u03b9\u03bb\u03b5\u03b3\u03b5\u03af \u03ba\u03ac\u03bc\u03b5\u03c1\u03b1",
    noCamerasFound: "\u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b1\u03bd \u03ba\u03ac\u03bc\u03b5\u03c1\u03b5\u03c2",
    noCamerasFoundSentence: "\u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b1\u03bd \u03ba\u03ac\u03bc\u03b5\u03c1\u03b5\u03c2.",
    noRecordingsForDate: "\u0394\u03b5\u03bd \u03c5\u03c0\u03ac\u03c1\u03c7\u03bf\u03c5\u03bd \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ad\u03c2 \u03b3\u03b9\u03b1 \u03b1\u03c5\u03c4\u03ae\u03bd \u03c4\u03b7\u03bd \u03b7\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b1.",
    noRecordingsReady: "\u0394\u03b5\u03bd \u03c5\u03c0\u03ac\u03c1\u03c7\u03bf\u03c5\u03bd \u03ad\u03c4\u03bf\u03b9\u03bc\u03b5\u03c2 \u03b7\u03c7\u03bf\u03b3\u03c1\u03b1\u03c6\u03ae\u03c3\u03b5\u03b9\u03c2",
    noThumbnail: "\u03a7\u03c9\u03c1\u03af\u03c2 \u03bc\u03b9\u03ba\u03c1\u03bf\u03b3\u03c1\u03b1\u03c6\u03af\u03b1",
    noneYet: "\u039a\u03b1\u03bc\u03af\u03b1 \u03b1\u03ba\u03cc\u03bc\u03b1",
    notCached: "\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03b1\u03c0\u03bf\u03b8\u03b7\u03ba\u03b5\u03c5\u03c4\u03b5\u03af \u03c3\u03c4\u03b7\u03bd \u03ba\u03c1\u03c5\u03c6\u03ae \u03bc\u03bd\u03ae\u03bc\u03b7",
    offline: "\u03b5\u03ba\u03c4\u03cc\u03c2 \u03c3\u03cd\u03bd\u03b4\u03b5\u03c3\u03b7\u03c2",
    offlineCount: "{count} \u03b5\u03ba\u03c4\u03cc\u03c2 \u03c3\u03cd\u03bd\u03b4\u03b5\u03c3\u03b7\u03c2",
    online: "online",
    preparing: "\u03a0\u03c1\u03bf\u03b5\u03c4\u03bf\u03b9\u03bc\u03b1\u03c3\u03af\u03b1",
    preparingRecording: "\u03a0\u03c1\u03bf\u03b5\u03c4\u03bf\u03b9\u03bc\u03b1\u03c3\u03af\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae\u03c2...",
    ready: "\u0388\u03c4\u03bf\u03b9\u03bc\u03bf\u03b9",
    readyToWatch: "\u0388\u03c4\u03bf\u03b9\u03bc\u03bf \u03b3\u03b9\u03b1 \u03c0\u03b1\u03c1\u03b1\u03ba\u03bf\u03bb\u03bf\u03cd\u03b8\u03b7\u03c3\u03b7",
    recordingEmpty: "\u0397 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03b5\u03af\u03bd\u03b1\u03b9 \u03ac\u03b4\u03b5\u03b9\u03b1",
    recordingIsNotReady: "\u0397 \u03b7\u03c7\u03bf\u03b3\u03c1\u03ac\u03c6\u03b7\u03c3\u03b7 \u03b4\u03b5\u03bd \u03b5\u03af\u03bd\u03b1\u03b9 \u03b1\u03ba\u03cc\u03bc\u03b1 \u03ad\u03c4\u03bf\u03b9\u03bc\u03b7.",
    recordingIsNotReadyStatus: "\u0397 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03b4\u03b5\u03bd \u03b5\u03af\u03bd\u03b1\u03b9 \u03ad\u03c4\u03bf\u03b9\u03bc\u03b7 ({status})",
    recordingsCountStatus: "{shown} \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ce\u03bd {total} - {state}",
    recordingsReady: "\u039f\u03b9 \u03b7\u03c7\u03bf\u03b3\u03c1\u03b1\u03c6\u03ae\u03c3\u03b5\u03b9\u03c2 \u03b5\u03af\u03bd\u03b1\u03b9 \u03ad\u03c4\u03bf\u03b9\u03bc\u03b5\u03c2",
    refresh: "\u0391\u03bd\u03b1\u03bd\u03ad\u03c9\u03c3\u03b7",
    selectRecordingToPlay: "\u0395\u03c0\u03b9\u03bb\u03ad\u03be\u03c4\u03b5 \u03bc\u03b9\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03b3\u03b9\u03b1 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae",
    storageUsed: "\u0391\u03c0\u03bf\u03b8\u03ae\u03ba\u03b5\u03c5\u03c3\u03b7 \u03c0\u03bf\u03c5 \u03c7\u03c1\u03b7\u03c3\u03b9\u03bc\u03bf\u03c0\u03bf\u03b9\u03b5\u03af\u03c4\u03b1\u03b9",
    stillSyncing: "{count} \u03b5\u03be\u03b1\u03ba\u03bf\u03bb\u03bf\u03c5\u03b8\u03b5\u03af \u03bd\u03b1 \u03c3\u03c5\u03b3\u03c7\u03c1\u03bf\u03bd\u03af\u03b6\u03b5\u03c4\u03b1\u03b9",
    couldNotLoadHlsPlayer: "\u0394\u03b5\u03bd \u03ae\u03c4\u03b1\u03bd \u03b4\u03c5\u03bd\u03b1\u03c4\u03ae \u03b7 \u03c6\u03cc\u03c1\u03c4\u03c9\u03c3\u03b7 \u03c4\u03bf\u03c5 \u03c0\u03c1\u03bf\u03b3\u03c1\u03ac\u03bc\u03bc\u03b1\u03c4\u03bf\u03c2 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae\u03c2 HLS",
    date: "\u0397\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b1",
  },
  "es": {
    allCamerasOffline: "Todas las c\u00e1maras sin conexi\u00f3n",
    allCamerasOnline: "Todas las c\u00e1maras en l\u00ednea",
    allCaughtUp: "todos atrapados",
    back: "Atr\u00e1s",
    backgroundSyncControlsVisibility: "La sincronizaci\u00f3n en segundo plano controla la visibilidad",
    cached: "En cach\u00e9",
    camera: "c\u00e1mara",
    camerasOnline: "C\u00e1maras en l\u00ednea",
    genericCamera: "c\u00e1mara",
    hlsPlaybackFailed: "Error en la reproducci\u00f3n de HLS",
    hlsPlaybackUnsupported: "Este navegador no admite la reproducci\u00f3n de HLS",
    lazyCacheOnPlayback: "Cach\u00e9 diferido en reproducci\u00f3n",
    loading: "Cargando",
    loadingRecordings: "Cargando grabaciones...",
    newestRecording: "Grabaci\u00f3n m\u00e1s reciente",
    noCameraSelected: "Ninguna c\u00e1mara seleccionada",
    noCamerasFound: "No se encontraron c\u00e1maras",
    noCamerasFoundSentence: "No se encontraron c\u00e1maras.",
    noRecordingsForDate: "No hay grabaciones para esta fecha.",
    noRecordingsReady: "No hay grabaciones listas",
    noThumbnail: "Sin miniatura",
    noneYet: "Ninguno todav\u00eda",
    notCached: "No almacenado en cach\u00e9",
    offline: "fuera de l\u00ednea",
    offlineCount: "{count} fuera de l\u00ednea",
    online: "en l\u00ednea",
    preparing: "preparando",
    preparingRecording: "Preparando grabaci\u00f3n...",
    ready: "Listo",
    readyToWatch: "Listo para mirar",
    recordingEmpty: "La grabaci\u00f3n est\u00e1 vac\u00eda",
    recordingIsNotReady: "La grabaci\u00f3n a\u00fan no est\u00e1 lista.",
    recordingIsNotReadyStatus: "La grabaci\u00f3n no est\u00e1 lista ({status})",
    recordingsCountStatus: "{shown} de grabaciones {total} - {state}",
    recordingsReady: "Las grabaciones est\u00e1n listas",
    refresh: "Actualizar",
    selectRecordingToPlay: "Seleccione una grabaci\u00f3n para reproducir",
    storageUsed: "Almacenamiento utilizado",
    stillSyncing: "{count} sigue sincroniz\u00e1ndose",
    couldNotLoadHlsPlayer: "No se pudo cargar el reproductor HLS",
    date: "Fecha",
  },
  "et": {
    allCamerasOffline: "K\u00f5ik kaamerad v\u00f5rgu\u00fchenduseta",
    allCamerasOnline: "K\u00f5ik kaamerad v\u00f5rgus",
    allCaughtUp: "K\u00f5ik j\u00f5udsid j\u00e4rele",
    back: "Tagasi",
    backgroundSyncControlsVisibility: "Taustal s\u00fcnkroonimine juhib n\u00e4htavust",
    cached: "Vahem\u00e4llu salvestatud",
    camera: "Kaamera",
    camerasOnline: "Kaamerad Internetis",
    genericCamera: "Kaamera",
    hlsPlaybackFailed: "HLS taasesitus eba\u00f5nnestus",
    hlsPlaybackUnsupported: "See brauser ei toeta HLS taasesitust",
    lazyCacheOnPlayback: "Laisk vahem\u00e4lu taasesitusel",
    loading: "Laadimine",
    loadingRecordings: "Salvestiste laadimine...",
    newestRecording: "Uusim salvestus",
    noCameraSelected: "Kaamerat pole valitud",
    noCamerasFound: "Kaameraid ei leitud",
    noCamerasFoundSentence: "Kaameraid ei leitud.",
    noRecordingsForDate: "Sellel kuup\u00e4eval pole salvestusi.",
    noRecordingsReady: "Salvestisi pole valmis",
    noThumbnail: "Pisipilti pole",
    noneYet: "Veel mitte \u00fchtegi",
    notCached: "Pole vahem\u00e4llu salvestatud",
    offline: "v\u00f5rgu\u00fchenduseta",
    offlineCount: "{count} v\u00f5rgu\u00fchenduseta",
    online: "v\u00f5rgus",
    preparing: "Ettevalmistus",
    preparingRecording: "Salvestamise ettevalmistamine...",
    ready: "Valmis",
    readyToWatch: "Vaatamiseks valmis",
    recordingEmpty: "Salvestus on t\u00fchi",
    recordingIsNotReady: "Salvestamine pole veel valmis.",
    recordingIsNotReadyStatus: "Salvestamine pole valmis ({status})",
    recordingsCountStatus: "{shown}/{total} salvestist \u2013 {state}",
    recordingsReady: "Salvestised on valmis",
    refresh: "V\u00e4rskenda",
    selectRecordingToPlay: "Valige esitamiseks salvestis",
    storageUsed: "Ladustamine kasutatud",
    stillSyncing: "{count} on endiselt s\u00fcnkroonimisel",
    couldNotLoadHlsPlayer: "HLS pleierit ei saanud laadida",
    date: "Kuup\u00e4ev",
  },
  "fa": {
    allCamerasOffline: "\u0647\u0645\u0647 \u062f\u0648\u0631\u0628\u06cc\u0646 \u0647\u0627 \u0622\u0641\u0644\u0627\u06cc\u0646",
    allCamerasOnline: "\u0647\u0645\u0647 \u062f\u0648\u0631\u0628\u06cc\u0646 \u0647\u0627 \u0622\u0646\u0644\u0627\u06cc\u0646",
    allCaughtUp: "\u0647\u0645\u0647 \u06af\u0631\u0641\u062a\u0627\u0631 \u0634\u062f\u0646\u062f",
    back: "\u0628\u0631\u06af\u0634\u062a",
    backgroundSyncControlsVisibility: "\u0647\u0645\u06af\u0627\u0645\u200c\u0633\u0627\u0632\u06cc \u067e\u0633\u200c\u0632\u0645\u06cc\u0646\u0647\u060c \u062f\u06cc\u062f \u0631\u0627 \u06a9\u0646\u062a\u0631\u0644 \u0645\u06cc\u200c\u06a9\u0646\u062f",
    cached: "\u0630\u062e\u06cc\u0631\u0647 \u0634\u062f\u0647 \u0627\u0633\u062a",
    camera: "\u062f\u0648\u0631\u0628\u06cc\u0646",
    camerasOnline: "\u062f\u0648\u0631\u0628\u06cc\u0646 \u0647\u0627\u06cc \u0622\u0646\u0644\u0627\u06cc\u0646",
    genericCamera: "\u062f\u0648\u0631\u0628\u06cc\u0646",
    hlsPlaybackFailed: "\u067e\u062e\u0634 HLS \u0646\u0627\u0645\u0648\u0641\u0642 \u0628\u0648\u062f",
    hlsPlaybackUnsupported: "\u067e\u062e\u0634 HLS \u062a\u0648\u0633\u0637 \u0627\u06cc\u0646 \u0645\u0631\u0648\u0631\u06af\u0631 \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc \u0646\u0645\u06cc \u0634\u0648\u062f",
    lazyCacheOnPlayback: "\u06a9\u0634 \u062a\u0646\u0628\u0644 \u0647\u0646\u06af\u0627\u0645 \u067e\u062e\u0634",
    loading: "\u062f\u0631 \u062d\u0627\u0644 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc",
    loadingRecordings: "\u062f\u0631 \u062d\u0627\u0644 \u0628\u0627\u0631\u06af\u06cc\u0631\u06cc \u0645\u0648\u0627\u0631\u062f \u0636\u0628\u0637 \u0634\u062f\u0647...",
    newestRecording: "\u062c\u062f\u06cc\u062f\u062a\u0631\u06cc\u0646 \u0636\u0628\u0637",
    noCameraSelected: "\u0647\u06cc\u0686 \u062f\u0648\u0631\u0628\u06cc\u0646\u06cc \u0627\u0646\u062a\u062e\u0627\u0628 \u0646\u0634\u062f\u0647 \u0627\u0633\u062a",
    noCamerasFound: "\u0647\u06cc\u0686 \u062f\u0648\u0631\u0628\u06cc\u0646\u06cc \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f",
    noCamerasFoundSentence: "\u0647\u06cc\u0686 \u062f\u0648\u0631\u0628\u06cc\u0646\u06cc \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f",
    noRecordingsForDate: "\u0647\u06cc\u0686 \u0636\u0628\u0637\u06cc \u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 \u062a\u0627\u0631\u06cc\u062e \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.",
    noRecordingsReady: "\u0647\u06cc\u0686 \u0636\u0628\u0637\u06cc \u0622\u0645\u0627\u062f\u0647 \u0646\u06cc\u0633\u062a",
    noThumbnail: "\u0628\u062f\u0648\u0646 \u062a\u0635\u0648\u06cc\u0631 \u06a9\u0648\u0686\u06a9",
    noneYet: "\u0647\u0646\u0648\u0632 \u0647\u06cc\u0686 \u06a9\u062f\u0627\u0645",
    notCached: "\u0630\u062e\u06cc\u0631\u0647 \u0646\u0634\u062f\u0647 \u0627\u0633\u062a",
    offline: "\u0622\u0641\u0644\u0627\u06cc\u0646",
    offlineCount: "{count} \u0622\u0641\u0644\u0627\u06cc\u0646",
    online: "\u0622\u0646\u0644\u0627\u06cc\u0646",
    preparing: "\u0622\u0645\u0627\u062f\u0647 \u0633\u0627\u0632\u06cc",
    preparingRecording: "\u062f\u0631 \u062d\u0627\u0644 \u0622\u0645\u0627\u062f\u0647 \u0633\u0627\u0632\u06cc \u0636\u0628\u0637...",
    ready: "\u0622\u0645\u0627\u062f\u0647 \u0627\u0633\u062a",
    readyToWatch: "\u0622\u0645\u0627\u062f\u0647 \u062a\u0645\u0627\u0634\u0627",
    recordingEmpty: "\u0636\u0628\u0637 \u062e\u0627\u0644\u06cc \u0627\u0633\u062a",
    recordingIsNotReady: "\u0636\u0628\u0637 \u0647\u0646\u0648\u0632 \u0622\u0645\u0627\u062f\u0647 \u0646\u06cc\u0633\u062a.",
    recordingIsNotReadyStatus: "\u0636\u0628\u0637 \u0622\u0645\u0627\u062f\u0647 \u0646\u06cc\u0633\u062a ({status})",
    recordingsCountStatus: "{shown} \u0627\u0632 \u0636\u0628\u0637\u200c\u0647\u0627\u06cc {total} - {state}",
    recordingsReady: "\u0636\u0628\u0637 \u0647\u0627 \u0622\u0645\u0627\u062f\u0647 \u0627\u0633\u062a",
    refresh: "\u062a\u0627\u0632\u0647 \u06a9\u0631\u062f\u0646",
    selectRecordingToPlay: "\u0636\u0628\u0637 \u0631\u0627 \u0628\u0631\u0627\u06cc \u067e\u062e\u0634 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f",
    storageUsed: "\u0630\u062e\u06cc\u0631\u0647 \u0633\u0627\u0632\u06cc \u0627\u0633\u062a\u0641\u0627\u062f\u0647 \u0634\u062f\u0647",
    stillSyncing: "{count} \u0647\u0645\u0686\u0646\u0627\u0646 \u062f\u0631 \u062d\u0627\u0644 \u0647\u0645\u06af\u0627\u0645 \u0633\u0627\u0632\u06cc \u0627\u0633\u062a",
    couldNotLoadHlsPlayer: "\u067e\u062e\u0634 \u06a9\u0646\u0646\u062f\u0647 HLS \u0628\u0627\u0631\u06af\u06cc\u0631\u06cc \u0646\u0634\u062f",
    date: "\u062a\u0627\u0631\u06cc\u062e",
  },
  "fi": {
    allCamerasOffline: "Kaikki kamerat offline-tilassa",
    allCamerasOnline: "Kaikki kamerat verkossa",
    allCaughtUp: "Kaikki kiinni",
    back: "Takaisin",
    backgroundSyncControlsVisibility: "Taustan synkronointi ohjaa n\u00e4kyvyytt\u00e4",
    cached: "V\u00e4limuistissa",
    camera: "Kamera",
    camerasOnline: "Kamerat verkossa",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS -toisto ep\u00e4onnistui",
    hlsPlaybackUnsupported: "T\u00e4m\u00e4 selain ei tue HLS-toistoa",
    lazyCacheOnPlayback: "Laiska v\u00e4limuisti toistossa",
    loading: "Ladataan",
    loadingRecordings: "Ladataan tallenteita...",
    newestRecording: "Uusin tallenne",
    noCameraSelected: "Kameraa ei ole valittu",
    noCamerasFound: "Kameroita ei l\u00f6ytynyt",
    noCamerasFoundSentence: "Kameroita ei l\u00f6ytynyt.",
    noRecordingsForDate: "Ei tallenteita t\u00e4lle p\u00e4iv\u00e4lle.",
    noRecordingsReady: "Ei valmiita tallenteita",
    noThumbnail: "Ei pikkukuvaa",
    noneYet: "Ei viel\u00e4 yht\u00e4\u00e4n",
    notCached: "Ei v\u00e4limuistissa",
    offline: "offline-tilassa",
    offlineCount: "{count} offline-tilassa",
    online: "verkossa",
    preparing: "Valmistellaan",
    preparingRecording: "Valmistellaan tallennusta...",
    ready: "Valmis",
    readyToWatch: "Valmiina katsomaan",
    recordingEmpty: "Tallennus on tyhj\u00e4",
    recordingIsNotReady: "Tallennus ei ole viel\u00e4 valmis.",
    recordingIsNotReadyStatus: "Tallennus ei ole valmis ({status})",
    recordingsCountStatus: "{shown}/{total}-tallenteet \u2013 {state}",
    recordingsReady: "Tallenteet ovat valmiina",
    refresh: "P\u00e4ivit\u00e4",
    selectRecordingToPlay: "Valitse toistettava tallenne",
    storageUsed: "S\u00e4ilytys k\u00e4ytetty",
    stillSyncing: "{count} synkronoidaan edelleen",
    couldNotLoadHlsPlayer: "HLS-soitinta ei voitu ladata",
    date: "P\u00e4iv\u00e4m\u00e4\u00e4r\u00e4",
  },
  "fr": {
    allCamerasOffline: "Toutes les cam\u00e9ras hors ligne",
    allCamerasOnline: "Toutes les cam\u00e9ras en ligne",
    allCaughtUp: "Tous rattrap\u00e9s",
    back: "Retour",
    backgroundSyncControlsVisibility: "La synchronisation en arri\u00e8re-plan contr\u00f4le la visibilit\u00e9",
    cached: "En cache",
    camera: "Appareil photo",
    camerasOnline: "Cam\u00e9ras en ligne",
    genericCamera: "Appareil photo",
    hlsPlaybackFailed: "\u00c9chec de la lecture de HLS",
    hlsPlaybackUnsupported: "La lecture HLS n'est pas prise en charge par ce navigateur",
    lazyCacheOnPlayback: "Cache paresseux lors de la lecture",
    loading: "Chargement",
    loadingRecordings: "Chargement des enregistrements...",
    newestRecording: "Enregistrement le plus r\u00e9cent",
    noCameraSelected: "Aucune cam\u00e9ra s\u00e9lectionn\u00e9e",
    noCamerasFound: "Aucune cam\u00e9ra trouv\u00e9e",
    noCamerasFoundSentence: "Aucune cam\u00e9ra trouv\u00e9e.",
    noRecordingsForDate: "Aucun enregistrement pour cette date.",
    noRecordingsReady: "Aucun enregistrement pr\u00eat",
    noThumbnail: "Aucune vignette",
    noneYet: "Aucun pour l'instant",
    notCached: "Non mis en cache",
    offline: "hors ligne",
    offlineCount: "{count} hors ligne",
    online: "en ligne",
    preparing: "Pr\u00e9paration",
    preparingRecording: "Pr\u00e9paration de l'enregistrement...",
    ready: "Pr\u00eat",
    readyToWatch: "Pr\u00eat \u00e0 regarder",
    recordingEmpty: "L'enregistrement est vide",
    recordingIsNotReady: "L'enregistrement n'est pas encore pr\u00eat.",
    recordingIsNotReadyStatus: "L'enregistrement n'est pas pr\u00eat ({status})",
    recordingsCountStatus: "{shown} sur {total} enregistrements - {state}",
    recordingsReady: "Les enregistrements sont pr\u00eats",
    refresh: "Actualiser",
    selectRecordingToPlay: "S\u00e9lectionnez un enregistrement \u00e0 lire",
    storageUsed: "Stockage utilis\u00e9",
    stillSyncing: "{count} est toujours en cours de synchronisation",
    couldNotLoadHlsPlayer: "Impossible de charger le lecteur HLS",
    date: "Date",
  },
  "he": {
    allCamerasOffline: "\u05db\u05dc \u05d4\u05de\u05e6\u05dc\u05de\u05d5\u05ea \u05d1\u05de\u05e6\u05d1 \u05dc\u05d0 \u05de\u05e7\u05d5\u05d5\u05df",
    allCamerasOnline: "\u05db\u05dc \u05d4\u05de\u05e6\u05dc\u05de\u05d5\u05ea \u05d1\u05d0\u05d9\u05e0\u05d8\u05e8\u05e0\u05d8",
    allCaughtUp: "\u05d4\u05db\u05dc \u05ea\u05e4\u05e1",
    back: "\u05d7\u05d6\u05e8\u05d4",
    backgroundSyncControlsVisibility: "\u05e1\u05e0\u05db\u05e8\u05d5\u05df \u05d1\u05e8\u05e7\u05e2 \u05e9\u05d5\u05dc\u05d8 \u05d1\u05e0\u05e8\u05d0\u05d5\u05ea",
    cached: "\u05e9\u05de\u05d5\u05e8 \u05d1\u05de\u05d8\u05de\u05d5\u05df",
    camera: "\u05de\u05e6\u05dc\u05de\u05d4",
    camerasOnline: "\u05de\u05e6\u05dc\u05de\u05d5\u05ea \u05d1\u05d0\u05d9\u05e0\u05d8\u05e8\u05e0\u05d8",
    genericCamera: "\u05de\u05e6\u05dc\u05de\u05d4",
    hlsPlaybackFailed: "\u05d4\u05e4\u05e2\u05dc\u05ea HLS \u05e0\u05db\u05e9\u05dc\u05d4",
    hlsPlaybackUnsupported: "\u05d4\u05e4\u05e2\u05dc\u05ea HLS \u05d0\u05d9\u05e0\u05d4 \u05e0\u05ea\u05de\u05db\u05ea \u05e2\u05dc \u05d9\u05d3\u05d9 \u05d3\u05e4\u05d3\u05e4\u05df \u05d6\u05d4",
    lazyCacheOnPlayback: "\u05de\u05d8\u05de\u05d5\u05df \u05e2\u05e6\u05dc\u05df \u05d1\u05d4\u05e9\u05de\u05e2\u05d4",
    loading: "\u05d8\u05d5\u05e2\u05df",
    loadingRecordings: "\u05d8\u05d5\u05e2\u05df \u05d4\u05e7\u05dc\u05d8\u05d5\u05ea...",
    newestRecording: "\u05d4\u05d4\u05e7\u05dc\u05d8\u05d4 \u05d4\u05d7\u05d3\u05e9\u05d4 \u05d1\u05d9\u05d5\u05ea\u05e8",
    noCameraSelected: "\u05dc\u05d0 \u05e0\u05d1\u05d7\u05e8\u05d4 \u05de\u05e6\u05dc\u05de\u05d4",
    noCamerasFound: "\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0\u05d5 \u05de\u05e6\u05dc\u05de\u05d5\u05ea",
    noCamerasFoundSentence: "\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0\u05d5 \u05de\u05e6\u05dc\u05de\u05d5\u05ea.",
    noRecordingsForDate: "\u05d0\u05d9\u05df \u05d4\u05e7\u05dc\u05d8\u05d5\u05ea \u05dc\u05ea\u05d0\u05e8\u05d9\u05da \u05d6\u05d4.",
    noRecordingsReady: "\u05d0\u05d9\u05df \u05d4\u05e7\u05dc\u05d8\u05d5\u05ea \u05de\u05d5\u05db\u05e0\u05d5\u05ea",
    noThumbnail: "\u05d0\u05d9\u05df \u05ea\u05de\u05d5\u05e0\u05d4 \u05de\u05de\u05d5\u05d6\u05e2\u05e8\u05ea",
    noneYet: "\u05e2\u05d3\u05d9\u05d9\u05df \u05d0\u05d9\u05df",
    notCached: "\u05dc\u05d0 \u05e9\u05de\u05d5\u05e8",
    offline: "\u05d1\u05de\u05e6\u05d1 \u05dc\u05d0 \u05de\u05e7\u05d5\u05d5\u05df",
    offlineCount: "{count} \u05d1\u05de\u05e6\u05d1 \u05dc\u05d0 \u05de\u05e7\u05d5\u05d5\u05df",
    online: "\u05d1\u05d0\u05d9\u05e0\u05d8\u05e8\u05e0\u05d8",
    preparing: "\u05de\u05ea\u05db\u05d5\u05e0\u05e0\u05ea",
    preparingRecording: "\u05de\u05db\u05d9\u05df \u05d4\u05e7\u05dc\u05d8\u05d4...",
    ready: "\u05de\u05d5\u05db\u05df",
    readyToWatch: "\u05de\u05d5\u05db\u05df \u05dc\u05e6\u05e4\u05d9\u05d9\u05d4",
    recordingEmpty: "\u05d4\u05d4\u05e7\u05dc\u05d8\u05d4 \u05e8\u05d9\u05e7\u05d4",
    recordingIsNotReady: "\u05d4\u05d4\u05e7\u05dc\u05d8\u05d4 \u05e2\u05d3\u05d9\u05d9\u05df \u05dc\u05d0 \u05de\u05d5\u05db\u05e0\u05d4.",
    recordingIsNotReadyStatus: "\u05d4\u05d4\u05e7\u05dc\u05d8\u05d4 \u05dc\u05d0 \u05de\u05d5\u05db\u05e0\u05d4 ({status})",
    recordingsCountStatus: "{shown} \u05e9\u05dc \u05d4\u05e7\u05dc\u05d8\u05d5\u05ea {total} - {state}",
    recordingsReady: "\u05d4\u05d4\u05e7\u05dc\u05d8\u05d5\u05ea \u05de\u05d5\u05db\u05e0\u05d5\u05ea",
    refresh: "\u05e8\u05e2\u05e0\u05df",
    selectRecordingToPlay: "\u05d1\u05d7\u05e8 \u05d4\u05e7\u05dc\u05d8\u05d4 \u05dc\u05d4\u05e4\u05e2\u05dc\u05d4",
    storageUsed: "\u05d0\u05d7\u05e1\u05d5\u05df \u05d1\u05e9\u05d9\u05de\u05d5\u05e9",
    stillSyncing: "{count} \u05e2\u05d3\u05d9\u05d9\u05df \u05de\u05e1\u05ea\u05e0\u05db\u05e8\u05df",
    couldNotLoadHlsPlayer: "\u05dc\u05d0 \u05e0\u05d9\u05ea\u05df \u05dc\u05d8\u05e2\u05d5\u05df \u05d0\u05ea \u05e0\u05d2\u05df HLS",
    date: "\u05ea\u05d0\u05e8\u05d9\u05da",
  },
  "hi": {
    allCamerasOffline: "\u0938\u092d\u0940 \u0915\u0948\u092e\u0930\u0947 \u0911\u092b\u093c\u0932\u093e\u0907\u0928",
    allCamerasOnline: "\u0938\u092d\u0940 \u0915\u0948\u092e\u0930\u0947 \u0911\u0928\u0932\u093e\u0907\u0928",
    allCaughtUp: "\u0938\u092d\u0940 \u0915\u094b \u092a\u0915\u0921\u093c \u0932\u093f\u092f\u093e \u0917\u092f\u093e",
    back: "\u0935\u093e\u092a\u0938",
    backgroundSyncControlsVisibility: "\u092c\u0948\u0915\u0917\u094d\u0930\u093e\u0909\u0902\u0921 \u0938\u093f\u0902\u0915 \u0926\u0943\u0936\u094d\u092f\u0924\u093e \u0915\u094b \u0928\u093f\u092f\u0902\u0924\u094d\u0930\u093f\u0924 \u0915\u0930\u0924\u093e \u0939\u0948",
    cached: "\u0915\u0948\u0936\u094d\u0921",
    camera: "\u0915\u0948\u092e\u0930\u093e",
    camerasOnline: "\u0915\u0948\u092e\u0930\u0947 \u0911\u0928\u0932\u093e\u0907\u0928",
    genericCamera: "\u0915\u0948\u092e\u0930\u093e",
    hlsPlaybackFailed: "HLS \u092a\u094d\u0932\u0947\u092c\u0948\u0915 \u0935\u093f\u092b\u0932 \u0930\u0939\u093e",
    hlsPlaybackUnsupported: "HLS \u092a\u094d\u0932\u0947\u092c\u0948\u0915 \u0907\u0938 \u092c\u094d\u0930\u093e\u0909\u091c\u093c\u0930 \u0926\u094d\u0935\u093e\u0930\u093e \u0938\u092e\u0930\u094d\u0925\u093f\u0924 \u0928\u0939\u0940\u0902 \u0939\u0948",
    lazyCacheOnPlayback: "\u092a\u094d\u0932\u0947\u092c\u0948\u0915 \u092a\u0930 \u0906\u0932\u0938\u0940 \u0915\u0948\u0936",
    loading: "\u0932\u094b\u0921 \u0939\u094b \u0930\u0939\u093e \u0939\u0948",
    loadingRecordings: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0932\u094b\u0921 \u0939\u094b \u0930\u0939\u0940 \u0939\u0948...",
    newestRecording: "\u0928\u0935\u0940\u0928\u0924\u092e \u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917",
    noCameraSelected: "\u0915\u094b\u0908 \u0915\u0948\u092e\u0930\u093e \u091a\u092f\u0928\u093f\u0924 \u0928\u0939\u0940\u0902",
    noCamerasFound: "\u0915\u094b\u0908 \u0915\u0948\u092e\u0930\u093e \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e",
    noCamerasFoundSentence: "\u0915\u094b\u0908 \u0915\u0948\u092e\u0930\u093e \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e.",
    noRecordingsForDate: "\u0907\u0938 \u0924\u093f\u0925\u093f \u0915\u0947 \u0932\u093f\u090f \u0915\u094b\u0908 \u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0928\u0939\u0940\u0902.",
    noRecordingsReady: "\u0915\u094b\u0908 \u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0924\u0948\u092f\u093e\u0930 \u0928\u0939\u0940\u0902",
    noThumbnail: "\u0915\u094b\u0908 \u0925\u0902\u092c\u0928\u0947\u0932 \u0928\u0939\u0940\u0902",
    noneYet: "\u0905\u092d\u0940 \u0924\u0915 \u0915\u094b\u0908 \u0928\u0939\u0940\u0902",
    notCached: "\u0915\u0948\u0936 \u0928\u0939\u0940\u0902 \u0915\u093f\u092f\u093e \u0917\u092f\u093e",
    offline: "\u0911\u092b\u093c\u0932\u093e\u0907\u0928",
    offlineCount: "\u0915\u093e\u0909\u0902\u091f\u092a\u094d\u0932\u0947\u0938\u0939\u094b\u0932\u094d\u0921\u0930 \u0911\u092b\u093c\u0932\u093e\u0907\u0928",
    online: "\u0911\u0928\u0932\u093e\u0907\u0928",
    preparing: "\u0924\u0948\u092f\u093e\u0930\u0940",
    preparingRecording: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0924\u0948\u092f\u093e\u0930 \u0915\u0940 \u091c\u093e \u0930\u0939\u0940 \u0939\u0948...",
    ready: "\u0924\u0948\u092f\u093e\u0930",
    readyToWatch: "\u0926\u0947\u0916\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u0924\u0948\u092f\u093e\u0930",
    recordingEmpty: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0916\u093e\u0932\u0940 \u0939\u0948",
    recordingIsNotReady: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0905\u092d\u0940 \u0924\u0948\u092f\u093e\u0930 \u0928\u0939\u0940\u0902 \u0939\u0948.",
    recordingIsNotReadyStatus: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0924\u0948\u092f\u093e\u0930 \u0928\u0939\u0940\u0902 \u0939\u0948 (\u0938\u094d\u091f\u0947\u091f\u0938\u092a\u094d\u0932\u0947\u0938\u0939\u094b\u0932\u094d\u0921\u0930)",
    recordingsCountStatus: "\u091f\u094b\u091f\u0932\u092a\u094d\u0932\u0947\u0938\u0939\u094b\u0932\u094d\u0921\u0930 \u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0915\u093e \u0926\u093f\u0916\u093e\u092f\u093e \u0917\u092f\u093e \u092a\u094d\u0932\u0947\u0938\u0939\u094b\u0932\u094d\u0921\u0930 - \u0938\u094d\u091f\u0947\u091f\u092a\u094d\u0932\u0947\u0938\u0939\u094b\u0932\u094d\u0921\u0930",
    recordingsReady: "\u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u0924\u0948\u092f\u093e\u0930 \u0939\u0948\u0902",
    refresh: "\u0924\u093e\u091c\u093c\u093e \u0915\u0930\u0947\u0902",
    selectRecordingToPlay: "\u091a\u0932\u093e\u0928\u0947 \u0915\u0947 \u0932\u093f\u090f \u090f\u0915 \u0930\u093f\u0915\u0949\u0930\u094d\u0921\u093f\u0902\u0917 \u091a\u0941\u0928\u0947\u0902",
    storageUsed: "\u0909\u092a\u092f\u094b\u0917 \u0915\u093f\u092f\u093e \u0917\u092f\u093e \u092d\u0902\u0921\u093e\u0930\u0923",
    stillSyncing: "{count} \u0905\u092d\u0940 \u092d\u0940 \u0938\u093f\u0902\u0915 \u0939\u094b \u0930\u0939\u093e \u0939\u0948",
    couldNotLoadHlsPlayer: "HLS \u092a\u094d\u0932\u0947\u092f\u0930 \u0932\u094b\u0921 \u0928\u0939\u0940\u0902 \u0939\u094b \u0938\u0915\u093e",
    date: "\u0926\u093f\u0928\u093e\u0902\u0915",
  },
  "hr": {
    allCamerasOffline: "Sve kamere su izvan mre\u017ee",
    allCamerasOnline: "Sve kamere online",
    allCaughtUp: "Sve je nadokna\u0111eno",
    back: "natrag",
    backgroundSyncControlsVisibility: "Pozadinska sinkronizacija kontrolira vidljivost",
    cached: "Spremljeno u predmemoriju",
    camera: "Kamera",
    camerasOnline: "Kamere Online",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS reprodukcija nije uspjela",
    hlsPlaybackUnsupported: "HLS reprodukcija nije podr\u017eana u ovom pregledniku",
    lazyCacheOnPlayback: "Lijena predmemorija pri reprodukciji",
    loading: "U\u010ditavanje",
    loadingRecordings: "U\u010ditavanje snimaka...",
    newestRecording: "Najnovija snimka",
    noCameraSelected: "Nema odabrane kamere",
    noCamerasFound: "Nema prona\u0111enih kamera",
    noCamerasFoundSentence: "Nema prona\u0111enih kamera.",
    noRecordingsForDate: "Nema snimanja za ovaj datum.",
    noRecordingsReady: "Nema spremnih snimaka",
    noThumbnail: "Nema sli\u010dice",
    noneYet: "Jo\u0161 ni\u0161ta",
    notCached: "Nije predmemorirano",
    offline: "izvan mre\u017ee",
    offlineCount: "{count} izvan mre\u017ee",
    online: "online",
    preparing: "Priprema",
    preparingRecording: "Priprema snimanja...",
    ready: "spreman",
    readyToWatch: "Spremno za gledanje",
    recordingEmpty: "Snimak je prazan",
    recordingIsNotReady: "Snimanje jo\u0161 nije spremno.",
    recordingIsNotReadyStatus: "Snimanje nije spremno ({status})",
    recordingsCountStatus: "{shown} od {total} snimaka - {state}",
    recordingsReady: "Snimci su spremni",
    refresh: "Osvje\u017ei",
    selectRecordingToPlay: "Odaberite snimku za reprodukciju",
    storageUsed: "Iskori\u0161tena pohrana",
    stillSyncing: "{count} i dalje se sinkronizira",
    couldNotLoadHlsPlayer: "Nije mogu\u0107e u\u010ditati HLS player",
    date: "Datum",
  },
  "hu": {
    allCamerasOffline: "Minden kamera offline",
    allCamerasOnline: "Minden kamera online",
    allCaughtUp: "Mind felkapott",
    back: "Vissza",
    backgroundSyncControlsVisibility: "A h\u00e1tt\u00e9r szinkroniz\u00e1l\u00e1sa szab\u00e1lyozza a l\u00e1that\u00f3s\u00e1got",
    cached: "Gyors\u00edt\u00f3t\u00e1razott",
    camera: "F\u00e9nyk\u00e9pez\u0151g\u00e9p",
    camerasOnline: "Kamer\u00e1k Online",
    genericCamera: "F\u00e9nyk\u00e9pez\u0151g\u00e9p",
    hlsPlaybackFailed: "A HLS lej\u00e1tsz\u00e1s nem siker\u00fclt",
    hlsPlaybackUnsupported: "Ez a b\u00f6ng\u00e9sz\u0151 nem t\u00e1mogatja a HLS lej\u00e1tsz\u00e1st",
    lazyCacheOnPlayback: "Lusta gyors\u00edt\u00f3t\u00e1r lej\u00e1tsz\u00e1skor",
    loading: "Bet\u00f6lt\u00e9s",
    loadingRecordings: "Felv\u00e9telek bet\u00f6lt\u00e9se...",
    newestRecording: "Leg\u00fajabb felv\u00e9tel",
    noCameraSelected: "Nincs kamera kiv\u00e1lasztva",
    noCamerasFound: "Nem tal\u00e1lhat\u00f3 kamera",
    noCamerasFoundSentence: "Nem tal\u00e1lhat\u00f3 kamera.",
    noRecordingsForDate: "Nincsenek felv\u00e9telek erre a d\u00e1tumra.",
    noRecordingsReady: "Nincs k\u00e9sz felv\u00e9tel",
    noThumbnail: "Nincs indexk\u00e9p",
    noneYet: "M\u00e9g nincs",
    notCached: "Nincs gyors\u00edt\u00f3t\u00e1rban",
    offline: "offline m\u00f3dban",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Felk\u00e9sz\u00fcl\u00e9s",
    preparingRecording: "Felv\u00e9tel el\u0151k\u00e9sz\u00edt\u00e9se...",
    ready: "K\u00e9sz",
    readyToWatch: "Megtekint\u00e9sre k\u00e9sz",
    recordingEmpty: "A felv\u00e9tel \u00fcres",
    recordingIsNotReady: "A felv\u00e9tel m\u00e9g nincs k\u00e9sz.",
    recordingIsNotReadyStatus: "A felv\u00e9tel nem k\u00e9sz ({status})",
    recordingsCountStatus: "{shown}/{total} felv\u00e9tel \u2013 {state}",
    recordingsReady: "A felv\u00e9telek k\u00e9szen \u00e1llnak",
    refresh: "Friss\u00edt\u00e9s",
    selectRecordingToPlay: "V\u00e1lassza ki a lej\u00e1tszani k\u00edv\u00e1nt felv\u00e9telt",
    storageUsed: "T\u00e1rol\u00e1s haszn\u00e1lt",
    stillSyncing: "{count} m\u00e9g szinkroniz\u00e1lva",
    couldNotLoadHlsPlayer: "Nem siker\u00fclt bet\u00f6lteni a HLS lej\u00e1tsz\u00f3t",
    date: "D\u00e1tum",
  },
  "id": {
    allCamerasOffline: "Semua kamera offline",
    allCamerasOnline: "Semua kamera online",
    allCaughtUp: "Semua tertangkap",
    back: "Kembali",
    backgroundSyncControlsVisibility: "Sinkronisasi latar belakang mengontrol visibilitas",
    cached: "Di-cache",
    camera: "Kamera",
    camerasOnline: "Kamera Daring",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "Pemutaran HLS gagal",
    hlsPlaybackUnsupported: "Pemutaran HLS tidak didukung oleh browser ini",
    lazyCacheOnPlayback: "Cache malas saat pemutaran",
    loading: "Memuat",
    loadingRecordings: "Memuat rekaman...",
    newestRecording: "Rekaman Terbaru",
    noCameraSelected: "Tidak ada kamera yang dipilih",
    noCamerasFound: "Tidak ada kamera yang ditemukan",
    noCamerasFoundSentence: "Tidak ada kamera yang ditemukan.",
    noRecordingsForDate: "Tidak ada rekaman untuk tanggal ini.",
    noRecordingsReady: "Tidak ada rekaman yang siap",
    noThumbnail: "Tidak ada gambar kecil",
    noneYet: "Belum ada",
    notCached: "Tidak di-cache",
    offline: "luring",
    offlineCount: "{count} offline",
    online: "daring",
    preparing: "Mempersiapkan",
    preparingRecording: "Mempersiapkan rekaman...",
    ready: "Siap",
    readyToWatch: "Siap Menonton",
    recordingEmpty: "Rekaman kosong",
    recordingIsNotReady: "Perekaman belum siap.",
    recordingIsNotReadyStatus: "Rekaman belum siap ({status})",
    recordingsCountStatus: "{shown} dari rekaman {total} - {state}",
    recordingsReady: "Rekaman sudah siap",
    refresh: "Segarkan",
    selectRecordingToPlay: "Pilih rekaman untuk diputar",
    storageUsed: "Penyimpanan Digunakan",
    stillSyncing: "{count} masih disinkronkan",
    couldNotLoadHlsPlayer: "Tidak dapat memuat pemutar HLS",
    date: "Tanggal",
  },
  "it": {
    allCamerasOffline: "Tutte le telecamere offline",
    allCamerasOnline: "Tutte le telecamere online",
    allCaughtUp: "Tutto preso",
    back: "Indietro",
    backgroundSyncControlsVisibility: "La sincronizzazione in background controlla la visibilit\u00e0",
    cached: "Memorizzato nella cache",
    camera: "Fotocamera",
    camerasOnline: "Fotocamere in linea",
    genericCamera: "Fotocamera",
    hlsPlaybackFailed: "La riproduzione HLSPLACEholder non \u00e8 riuscita",
    hlsPlaybackUnsupported: "La riproduzione HLSPLACEholder non \u00e8 supportata da questo browser",
    lazyCacheOnPlayback: "Cache pigra durante la riproduzione",
    loading: "Caricamento",
    loadingRecordings: "Caricamento registrazioni...",
    newestRecording: "Registrazione pi\u00f9 recente",
    noCameraSelected: "Nessuna telecamera selezionata",
    noCamerasFound: "Nessuna fotocamera trovata",
    noCamerasFoundSentence: "Nessuna fotocamera trovata.",
    noRecordingsForDate: "Nessuna registrazione per questa data.",
    noRecordingsReady: "Nessuna registrazione pronta",
    noThumbnail: "Nessuna miniatura",
    noneYet: "Nessuno ancora",
    notCached: "Non memorizzato nella cache",
    offline: "non in linea",
    offlineCount: "COUNTPLACEholder offline",
    online: "in linea",
    preparing: "Preparazione",
    preparingRecording: "Preparazione della registrazione...",
    ready: "Pronto",
    readyToWatch: "Pronto per guardare",
    recordingEmpty: "La registrazione \u00e8 vuota",
    recordingIsNotReady: "La registrazione non \u00e8 ancora pronta.",
    recordingIsNotReadyStatus: "La registrazione non \u00e8 pronta (STATUSPLACEholder)",
    recordingsCountStatus: "SHOWNPLACEholder delle registrazioni TOTALPLACEholder - STATEPLACEholder",
    recordingsReady: "Le registrazioni sono pronte",
    refresh: "Aggiorna",
    selectRecordingToPlay: "Seleziona una registrazione da riprodurre",
    storageUsed: "Spazio di archiviazione utilizzato",
    stillSyncing: "COUNTPLACEholder ancora in fase di sincronizzazione",
    couldNotLoadHlsPlayer: "Impossibile caricare il lettore HLSPLACEholder",
    date: "Data",
  },
  "ja": {
    allCamerasOffline: "\u3059\u3079\u3066\u306e\u30ab\u30e1\u30e9\u304c\u30aa\u30d5\u30e9\u30a4\u30f3",
    allCamerasOnline: "\u3059\u3079\u3066\u306e\u30ab\u30e1\u30e9\u304c\u30aa\u30f3\u30e9\u30a4\u30f3\u306b",
    allCaughtUp: "\u5168\u90e8\u8ffd\u3044\u3064\u3044\u305f",
    back: "\u623b\u308b",
    backgroundSyncControlsVisibility: "\u30d0\u30c3\u30af\u30b0\u30e9\u30a6\u30f3\u30c9\u540c\u671f\u3067\u53ef\u8996\u6027\u3092\u5236\u5fa1",
    cached: "\u30ad\u30e3\u30c3\u30b7\u30e5\u3055\u308c\u305f",
    camera: "\u30ab\u30e1\u30e9",
    camerasOnline: "\u30aa\u30f3\u30e9\u30a4\u30f3\u30ab\u30e1\u30e9",
    genericCamera: "\u30ab\u30e1\u30e9",
    hlsPlaybackFailed: "HLS \u306e\u518d\u751f\u306b\u5931\u6557\u3057\u307e\u3057\u305f",
    hlsPlaybackUnsupported: "HLS \u306e\u518d\u751f\u306f\u3053\u306e\u30d6\u30e9\u30a6\u30b6\u3067\u306f\u30b5\u30dd\u30fc\u30c8\u3055\u308c\u3066\u3044\u307e\u305b\u3093",
    lazyCacheOnPlayback: "\u518d\u751f\u6642\u306e\u9045\u5ef6\u30ad\u30e3\u30c3\u30b7\u30e5",
    loading: "\u8aad\u307f\u8fbc\u307f\u4e2d",
    loadingRecordings: "\u9332\u97f3\u3092\u30ed\u30fc\u30c9\u4e2d...",
    newestRecording: "\u6700\u65b0\u306e\u9332\u97f3",
    noCameraSelected: "\u30ab\u30e1\u30e9\u304c\u9078\u629e\u3055\u308c\u3066\u3044\u307e\u305b\u3093",
    noCamerasFound: "\u30ab\u30e1\u30e9\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093",
    noCamerasFoundSentence: "\u30ab\u30e1\u30e9\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
    noRecordingsForDate: "\u3053\u306e\u65e5\u4ed8\u306e\u9332\u753b\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
    noRecordingsReady: "\u9332\u97f3\u306e\u6e96\u5099\u304c\u3067\u304d\u3066\u3044\u307e\u305b\u3093",
    noThumbnail: "\u30b5\u30e0\u30cd\u30a4\u30eb\u306a\u3057",
    noneYet: "\u307e\u3060\u3042\u308a\u307e\u305b\u3093",
    notCached: "\u30ad\u30e3\u30c3\u30b7\u30e5\u3055\u308c\u3066\u3044\u307e\u305b\u3093",
    offline: "\u30aa\u30d5\u30e9\u30a4\u30f3",
    offlineCount: "{count} \u304c\u30aa\u30d5\u30e9\u30a4\u30f3\u3067\u3059",
    online: "\u30aa\u30f3\u30e9\u30a4\u30f3",
    preparing: "\u6e96\u5099\u4e2d",
    preparingRecording: "\u9332\u97f3\u3092\u6e96\u5099\u3057\u3066\u3044\u307e\u3059...",
    ready: "\u6e96\u5099\u5b8c\u4e86",
    readyToWatch: "\u3059\u3050\u306b\u8996\u8074\u3067\u304d\u307e\u3059",
    recordingEmpty: "\u9332\u97f3\u304c\u7a7a\u3067\u3059",
    recordingIsNotReady: "\u307e\u3060\u9332\u97f3\u306e\u6e96\u5099\u304c\u3067\u304d\u3066\u3044\u307e\u305b\u3093\u3002",
    recordingIsNotReadyStatus: "\u9332\u97f3\u306e\u6e96\u5099\u304c\u3067\u304d\u3066\u3044\u307e\u305b\u3093 ({status})",
    recordingsCountStatus: "{total} \u9332\u97f3\u4e2d {shown} - {state}",
    recordingsReady: "\u9332\u97f3\u306e\u6e96\u5099\u304c\u3067\u304d\u307e\u3057\u305f",
    refresh: "\u30ea\u30d5\u30ec\u30c3\u30b7\u30e5",
    selectRecordingToPlay: "\u518d\u751f\u3059\u308b\u9332\u97f3\u3092\u9078\u629e\u3057\u307e\u3059",
    storageUsed: "\u4f7f\u7528\u6e08\u307f\u30b9\u30c8\u30ec\u30fc\u30b8",
    stillSyncing: "{count} \u306f\u307e\u3060\u540c\u671f\u4e2d\u3067\u3059",
    couldNotLoadHlsPlayer: "HLS \u30d7\u30ec\u30fc\u30e4\u30fc\u3092\u30ed\u30fc\u30c9\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f",
    date: "\u65e5\u4ed8",
  },
  "ko": {
    allCamerasOffline: "\ubaa8\ub4e0 \uce74\uba54\ub77c \uc624\ud504\ub77c\uc778",
    allCamerasOnline: "\ubaa8\ub4e0 \uce74\uba54\ub77c \uc628\ub77c\uc778",
    allCaughtUp: "\ubaa8\ub450 \ub530\ub77c\uc7a1\uc558\uc5b4",
    back: "\ub4a4\ub85c",
    backgroundSyncControlsVisibility: "\ubc31\uadf8\ub77c\uc6b4\ub4dc \ub3d9\uae30\ud654\uac00 \uac00\uc2dc\uc131\uc744 \uc81c\uc5b4\ud569\ub2c8\ub2e4.",
    cached: "\uce90\uc2dc\ub428",
    camera: "\uce74\uba54\ub77c",
    camerasOnline: "\uce74\uba54\ub77c \uc628\ub77c\uc778",
    genericCamera: "\uce74\uba54\ub77c",
    hlsPlaybackFailed: "HLS \uc7ac\uc0dd \uc2e4\ud328",
    hlsPlaybackUnsupported: "\uc774 \ube0c\ub77c\uc6b0\uc800\uc5d0\uc11c\ub294 HLS \uc7ac\uc0dd\uc774 \uc9c0\uc6d0\ub418\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.",
    lazyCacheOnPlayback: "\uc7ac\uc0dd \uc2dc \uc9c0\uc5f0 \uce90\uc2dc",
    loading: "\ub85c\ub4dc \uc911",
    loadingRecordings: "\ub179\uc74c \ub85c\ub4dc \uc911...",
    newestRecording: "\ucd5c\uc2e0 \ub179\uc74c",
    noCameraSelected: "\uc120\ud0dd\ud55c \uce74\uba54\ub77c\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
    noCamerasFound: "\uce74\uba54\ub77c\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
    noCamerasFoundSentence: "\uce74\uba54\ub77c\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
    noRecordingsForDate: "\ud574\ub2f9 \ub0a0\uc9dc\uc5d0 \ub300\ud55c \ub179\uc74c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.",
    noRecordingsReady: "\uc900\ube44\ub41c \ub179\uc74c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.",
    noThumbnail: "\ubbf8\ub9ac\ubcf4\uae30 \uc774\ubbf8\uc9c0 \uc5c6\uc74c",
    noneYet: "\uc544\uc9c1 \uc5c6\uc74c",
    notCached: "\uce90\uc2dc\ub418\uc9c0 \uc54a\uc74c",
    offline: "\uc624\ud504\ub77c\uc778",
    offlineCount: "{count} \uc624\ud504\ub77c\uc778",
    online: "\uc628\ub77c\uc778",
    preparing: "\uc900\ube44 \uc911",
    preparingRecording: "\ub179\uc74c \uc900\ube44 \uc911...",
    ready: "\uc900\ube44",
    readyToWatch: "\uc2dc\uccad \uc900\ube44 \uc644\ub8cc",
    recordingEmpty: "\ub179\uc74c \ub0b4\uc6a9\uc774 \ube44\uc5b4 \uc788\uc2b5\ub2c8\ub2e4.",
    recordingIsNotReady: "\uc544\uc9c1 \ub179\uc74c\uc774 \uc900\ube44\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.",
    recordingIsNotReadyStatus: "\ub179\ud654\uac00 \uc900\ube44\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4({status}).",
    recordingsCountStatus: "{total}\uac1c \ub179\uc74c \uc911 {shown}\uac1c - {state}",
    recordingsReady: "\ub179\uc74c \uc900\ube44 \uc644\ub8cc",
    refresh: "\uc0c8\ub85c\uace0\uce68",
    selectRecordingToPlay: "\uc7ac\uc0dd\ud560 \ub179\uc74c\uc744 \uc120\ud0dd\ud558\uc138\uc694",
    storageUsed: "\uc0ac\uc6a9\ub41c \uc800\uc7a5\uc18c",
    stillSyncing: "{count}\uac00 \uc544\uc9c1 \ub3d9\uae30\ud654 \uc911\uc785\ub2c8\ub2e4.",
    couldNotLoadHlsPlayer: "HLS \ud50c\ub808\uc774\uc5b4\ub97c \ub85c\ub4dc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
    date: "\ub0a0\uc9dc",
  },
  "lt": {
    allCamerasOffline: "Visos kameros neprisijungusios",
    allCamerasOnline: "Visos kameros internetu",
    allCaughtUp: "Visi pasivijo",
    back: "Atgal",
    backgroundSyncControlsVisibility: "Fono sinchronizavimas valdo matomum\u0105",
    cached: "Talpykloje",
    camera: "Fotoaparatas",
    camerasOnline: "Kameros internete",
    genericCamera: "Fotoaparatas",
    hlsPlaybackFailed: "HLS atkurti nepavyko",
    hlsPlaybackUnsupported: "\u0160i nar\u0161ykl\u0117 nepalaiko HLS atk\u016brimo",
    lazyCacheOnPlayback: "Tingi talpykla atk\u016brimo metu",
    loading: "\u012ekeliama",
    loadingRecordings: "\u012ekeliami \u012fra\u0161ai...",
    newestRecording: "Naujausias \u012fra\u0161as",
    noCameraSelected: "Nepasirinkta jokia kamera",
    noCamerasFound: "Nerasta joki\u0173 kamer\u0173",
    noCamerasFoundSentence: "Nerasta joki\u0173 kamer\u0173.",
    noRecordingsForDate: "N\u0117ra \u0161ios datos \u012fra\u0161\u0173.",
    noRecordingsReady: "N\u0117ra paruo\u0161t\u0173 \u012fra\u0161\u0173",
    noThumbnail: "N\u0117ra miniati\u016bros",
    noneYet: "Dar n\u0117 vieno",
    notCached: "Nei\u0161saugota talpykloje",
    offline: "neprisijungus",
    offlineCount: "{count} neprisijungus",
    online: "internete",
    preparing: "Ruo\u0161iamasi",
    preparingRecording: "Ruo\u0161iamas \u012fra\u0161ymas...",
    ready: "Paruo\u0161ta",
    readyToWatch: "Paruo\u0161ta \u017di\u016br\u0117ti",
    recordingEmpty: "\u012era\u0161as tu\u0161\u010dias",
    recordingIsNotReady: "\u012era\u0161ymas dar neparengtas.",
    recordingIsNotReadyStatus: "\u012era\u0161ymas neparengtas ({status})",
    recordingsCountStatus: "{shown} i\u0161 {total} \u012fra\u0161\u0173 \u2013 {state}",
    recordingsReady: "\u012era\u0161ai paruo\u0161ti",
    refresh: "Atnaujinti",
    selectRecordingToPlay: "Pasirinkite \u012fra\u0161\u0105, kur\u012f norite leisti",
    storageUsed: "Naudota saugykla",
    stillSyncing: "{count} vis dar sinchronizuojama",
    couldNotLoadHlsPlayer: "Nepavyko \u012fkelti HLS grotuvo",
    date: "Data",
  },
  "lv": {
    allCamerasOffline: "Visas kameras bezsaist\u0113",
    allCamerasOnline: "Visas kameras tie\u0161saist\u0113",
    allCaughtUp: "Visi pan\u0101ca",
    back: "Atpaka\u013c",
    backgroundSyncControlsVisibility: "Fona sinhroniz\u0101cija kontrol\u0113 redzam\u012bbu",
    cached: "Ke\u0161atmi\u0146\u0101 saglab\u0101ts",
    camera: "Kamera",
    camerasOnline: "Kameras tie\u0161saist\u0113",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS atska\u0146o\u0161ana neizdev\u0101s",
    hlsPlaybackUnsupported: "\u0160\u012b p\u0101rl\u016bkprogramma neatbalsta HLS atska\u0146o\u0161anu",
    lazyCacheOnPlayback: "Slinka ke\u0161atmi\u0146a atska\u0146o\u0161anas laik\u0101",
    loading: "Notiek iel\u0101de",
    loadingRecordings: "Notiek ierakstu iel\u0101de...",
    newestRecording: "Jaun\u0101kais ieraksts",
    noCameraSelected: "Nav atlas\u012bta neviena kamera",
    noCamerasFound: "Nav atrasta neviena kamera",
    noCamerasFoundSentence: "Nav atrasta neviena kamera.",
    noRecordingsForDate: "\u0160im datumam nav ierakstu.",
    noRecordingsReady: "Nav gatavs ieraksts",
    noThumbnail: "Nav s\u012bkt\u0113la",
    noneYet: "V\u0113l neviena",
    notCached: "Nav ke\u0161atmi\u0146\u0101",
    offline: "bezsaist\u0113",
    offlineCount: "{count} bezsaist\u0113",
    online: "tie\u0161saist\u0113",
    preparing: "Gatavo\u0161an\u0101s",
    preparingRecording: "Notiek ieraksta sagatavo\u0161ana...",
    ready: "Gatavs",
    readyToWatch: "Gatavs Skat\u012bties",
    recordingEmpty: "Ieraksts ir tuk\u0161s",
    recordingIsNotReady: "Ieraksts v\u0113l nav gatavs.",
    recordingIsNotReadyStatus: "Ieraksts nav gatavs ({status})",
    recordingsCountStatus: "{shown} no {total} ierakstiem\u00a0\u2014 {state}",
    recordingsReady: "Ieraksti ir gatavi",
    refresh: "Atsvaidzin\u0101t",
    selectRecordingToPlay: "Atlasiet atska\u0146ojamo ierakstu",
    storageUsed: "Uzglab\u0101\u0161ana Lietota",
    stillSyncing: "{count} joproj\u0101m sinhroniz\u0113",
    couldNotLoadHlsPlayer: "Nevar\u0113ja iel\u0101d\u0113t HLS atska\u0146ot\u0101ju",
    date: "Datums",
  },
  "nl": {
    allCamerasOffline: "Alle camera's offline",
    allCamerasOnline: "Alle camera's online",
    allCaughtUp: "Allemaal ingehaald",
    back: "Terug",
    backgroundSyncControlsVisibility: "Achtergrondsynchronisatie regelt de zichtbaarheid",
    cached: "In cache opgeslagen",
    camera: "Camera",
    camerasOnline: "Camera's online",
    genericCamera: "Camera",
    hlsPlaybackFailed: "Afspelen van HLS is mislukt",
    hlsPlaybackUnsupported: "HLS-weergave wordt niet ondersteund door deze browser",
    lazyCacheOnPlayback: "Lazy cache bij afspelen",
    loading: "Laden",
    loadingRecordings: "Opnames laden...",
    newestRecording: "Nieuwste opname",
    noCameraSelected: "Geen camera geselecteerd",
    noCamerasFound: "Geen camera's gevonden",
    noCamerasFoundSentence: "Geen camera's gevonden.",
    noRecordingsForDate: "Geen opnames voor deze datum.",
    noRecordingsReady: "Geen opnames gereed",
    noThumbnail: "Geen miniatuur",
    noneYet: "Nog geen",
    notCached: "Niet in de cache opgeslagen",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Voorbereiden",
    preparingRecording: "Opname voorbereiden...",
    ready: "Klaar",
    readyToWatch: "Klaar om te kijken",
    recordingEmpty: "Opname is leeg",
    recordingIsNotReady: "De opname is nog niet klaar.",
    recordingIsNotReadyStatus: "Opname is niet gereed ({status})",
    recordingsCountStatus: "{shown} van {total}-opnamen - {state}",
    recordingsReady: "Opnames zijn klaar",
    refresh: "Vernieuwen",
    selectRecordingToPlay: "Selecteer een opname om af te spelen",
    storageUsed: "Opslag gebruikt",
    stillSyncing: "{count} wordt nog gesynchroniseerd",
    couldNotLoadHlsPlayer: "Kan de HLS-speler niet laden",
    date: "Datum",
  },
  "no": {
    allCamerasOffline: "Alle kameraer er offline",
    allCamerasOnline: "Alle kameraer p\u00e5 nett",
    allCaughtUp: "Alle tok igjen",
    back: "Tilbake",
    backgroundSyncControlsVisibility: "Bakgrunnssynkronisering kontrollerer synlighet",
    cached: "Bufret",
    camera: "Kamera",
    camerasOnline: "Kameraer p\u00e5 nett",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS-avspilling mislyktes",
    hlsPlaybackUnsupported: "HLS-avspilling st\u00f8ttes ikke av denne nettleseren",
    lazyCacheOnPlayback: "Lazy cache ved avspilling",
    loading: "Laster",
    loadingRecordings: "Laster inn opptak...",
    newestRecording: "Nyeste opptak",
    noCameraSelected: "Ingen kamera valgt",
    noCamerasFound: "Ingen kameraer funnet",
    noCamerasFoundSentence: "Ingen kameraer funnet.",
    noRecordingsForDate: "Ingen opptak for denne datoen.",
    noRecordingsReady: "Ingen opptak er klare",
    noThumbnail: "Ingen miniatyrbilde",
    noneYet: "Ingen enn\u00e5",
    notCached: "Ikke bufret",
    offline: "offline",
    offlineCount: "{count} frakoblet",
    online: "p\u00e5 nett",
    preparing: "Forbereder",
    preparingRecording: "Forbereder opptak...",
    ready: "Klar",
    readyToWatch: "Klar til \u00e5 se",
    recordingEmpty: "Opptaket er tomt",
    recordingIsNotReady: "Opptaket er ikke klart enn\u00e5.",
    recordingIsNotReadyStatus: "Opptaket er ikke klart (STATUSPLASSHOLDER)",
    recordingsCountStatus: "{shown} av {total}-opptak - {state}",
    recordingsReady: "Opptakene er klare",
    refresh: "Oppdater",
    selectRecordingToPlay: "Velg et opptak som skal spilles av",
    storageUsed: "Oppbevaring brukt",
    stillSyncing: "{count} synkroniserer fortsatt",
    couldNotLoadHlsPlayer: "Kunne ikke laste HLS-spilleren",
    date: "Dato",
  },
  "pl": {
    allCamerasOffline: "Wszystkie kamery offline",
    allCamerasOnline: "Wszystkie kamery online",
    allCaughtUp: "Wszystko z\u0142apane",
    back: "Powr\u00f3t",
    backgroundSyncControlsVisibility: "Synchronizacja w tle kontroluje widoczno\u015b\u0107",
    cached: "Buforowane",
    camera: "Kamera",
    camerasOnline: "Kamery w Internecie",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "Odtwarzanie HLS nie powiod\u0142o si\u0119",
    hlsPlaybackUnsupported: "Ta przegl\u0105darka nie obs\u0142uguje odtwarzania HLS",
    lazyCacheOnPlayback: "Leniwa pami\u0119\u0107 podr\u0119czna podczas odtwarzania",
    loading: "\u0141adowanie",
    loadingRecordings: "\u0141adowanie nagra\u0144...",
    newestRecording: "Najnowsze nagranie",
    noCameraSelected: "Nie wybrano kamery",
    noCamerasFound: "Nie znaleziono kamer",
    noCamerasFoundSentence: "Nie znaleziono kamer.",
    noRecordingsForDate: "Brak nagra\u0144 dla tej daty.",
    noRecordingsReady: "Brak gotowych nagra\u0144",
    noThumbnail: "Brak miniatury",
    noneYet: "Jeszcze \u017caden",
    notCached: "Nie buforowane",
    offline: "nieaktywny",
    offlineCount: "{count} offline",
    online: "w Internecie",
    preparing: "Przygotowanie",
    preparingRecording: "Przygotowywanie nagrania...",
    ready: "Gotowy",
    readyToWatch: "Gotowy do ogl\u0105dania",
    recordingEmpty: "Nagranie jest puste",
    recordingIsNotReady: "Nagranie nie jest jeszcze gotowe.",
    recordingIsNotReadyStatus: "Nagranie nie jest gotowe ({status})",
    recordingsCountStatus: "{shown} nagra\u0144 {total} - {state}",
    recordingsReady: "Nagrania s\u0105 gotowe",
    refresh: "Od\u015bwie\u017c",
    selectRecordingToPlay: "Wybierz nagranie do odtworzenia",
    storageUsed: "Pami\u0119\u0107 u\u017cywana",
    stillSyncing: "{count} nadal si\u0119 synchronizuje",
    couldNotLoadHlsPlayer: "Nie mo\u017cna za\u0142adowa\u0107 odtwarzacza HLS",
    date: "Data",
  },
  "pt": {
    allCamerasOffline: "Todas as c\u00e2meras off-line",
    allCamerasOnline: "Todas as c\u00e2meras on-line",
    allCaughtUp: "Todos apanhados",
    back: "Voltar",
    backgroundSyncControlsVisibility: "A sincroniza\u00e7\u00e3o em segundo plano controla a visibilidade",
    cached: "Em cache",
    camera: "C\u00e2mera",
    camerasOnline: "C\u00e2meras on-line",
    genericCamera: "C\u00e2mera",
    hlsPlaybackFailed: "Falha na reprodu\u00e7\u00e3o de HLS",
    hlsPlaybackUnsupported: "A reprodu\u00e7\u00e3o HLS n\u00e3o \u00e9 suportada por este navegador",
    lazyCacheOnPlayback: "Cache lento na reprodu\u00e7\u00e3o",
    loading: "Carregando",
    loadingRecordings: "Carregando grava\u00e7\u00f5es...",
    newestRecording: "Grava\u00e7\u00e3o mais recente",
    noCameraSelected: "Nenhuma c\u00e2mera selecionada",
    noCamerasFound: "Nenhuma c\u00e2mera encontrada",
    noCamerasFoundSentence: "Nenhuma c\u00e2mera encontrada.",
    noRecordingsForDate: "N\u00e3o h\u00e1 grava\u00e7\u00f5es para esta data.",
    noRecordingsReady: "Nenhuma grava\u00e7\u00e3o pronta",
    noThumbnail: "Sem miniatura",
    noneYet: "Nenhum ainda",
    notCached: "N\u00e3o armazenado em cache",
    offline: "off-line",
    offlineCount: "{count} off-line",
    online: "on-line",
    preparing: "Preparando",
    preparingRecording: "Preparando grava\u00e7\u00e3o...",
    ready: "Pronto",
    readyToWatch: "Pronto para assistir",
    recordingEmpty: "A grava\u00e7\u00e3o est\u00e1 vazia",
    recordingIsNotReady: "A grava\u00e7\u00e3o ainda n\u00e3o est\u00e1 pronta.",
    recordingIsNotReadyStatus: "A grava\u00e7\u00e3o n\u00e3o est\u00e1 pronta ({status})",
    recordingsCountStatus: "{shown} de grava\u00e7\u00f5es {total} - {state}",
    recordingsReady: "As grava\u00e7\u00f5es est\u00e3o prontas",
    refresh: "Atualizar",
    selectRecordingToPlay: "Selecione uma grava\u00e7\u00e3o para reproduzir",
    storageUsed: "Armazenamento usado",
    stillSyncing: "{count} ainda sincronizando",
    couldNotLoadHlsPlayer: "N\u00e3o foi poss\u00edvel carregar o player HLS",
    date: "Data",
  },
  "pt-BR": {
    allCamerasOffline: "Todas as c\u00e2meras off-line",
    allCamerasOnline: "Todas as c\u00e2meras on-line",
    allCaughtUp: "Todos apanhados",
    back: "Voltar",
    backgroundSyncControlsVisibility: "A sincroniza\u00e7\u00e3o em segundo plano controla a visibilidade",
    cached: "Em cache",
    camera: "C\u00e2mera",
    camerasOnline: "C\u00e2meras on-line",
    genericCamera: "C\u00e2mera",
    hlsPlaybackFailed: "Falha na reprodu\u00e7\u00e3o de HLS",
    hlsPlaybackUnsupported: "A reprodu\u00e7\u00e3o HLS n\u00e3o \u00e9 suportada por este navegador",
    lazyCacheOnPlayback: "Cache lento na reprodu\u00e7\u00e3o",
    loading: "Carregando",
    loadingRecordings: "Carregando grava\u00e7\u00f5es...",
    newestRecording: "Grava\u00e7\u00e3o mais recente",
    noCameraSelected: "Nenhuma c\u00e2mera selecionada",
    noCamerasFound: "Nenhuma c\u00e2mera encontrada",
    noCamerasFoundSentence: "Nenhuma c\u00e2mera encontrada.",
    noRecordingsForDate: "N\u00e3o h\u00e1 grava\u00e7\u00f5es para esta data.",
    noRecordingsReady: "Nenhuma grava\u00e7\u00e3o pronta",
    noThumbnail: "Sem miniatura",
    noneYet: "Nenhum ainda",
    notCached: "N\u00e3o armazenado em cache",
    offline: "off-line",
    offlineCount: "{count} off-line",
    online: "on-line",
    preparing: "Preparando",
    preparingRecording: "Preparando grava\u00e7\u00e3o...",
    ready: "Pronto",
    readyToWatch: "Pronto para assistir",
    recordingEmpty: "A grava\u00e7\u00e3o est\u00e1 vazia",
    recordingIsNotReady: "A grava\u00e7\u00e3o ainda n\u00e3o est\u00e1 pronta.",
    recordingIsNotReadyStatus: "A grava\u00e7\u00e3o n\u00e3o est\u00e1 pronta ({status})",
    recordingsCountStatus: "{shown} de grava\u00e7\u00f5es {total} - {state}",
    recordingsReady: "As grava\u00e7\u00f5es est\u00e3o prontas",
    refresh: "Atualizar",
    selectRecordingToPlay: "Selecione uma grava\u00e7\u00e3o para reproduzir",
    storageUsed: "Armazenamento usado",
    stillSyncing: "{count} ainda sincronizando",
    couldNotLoadHlsPlayer: "N\u00e3o foi poss\u00edvel carregar o player HLS",
    date: "Data",
  },
  "ro": {
    allCamerasOffline: "Toate camerele offline",
    allCamerasOnline: "Toate camerele online",
    allCaughtUp: "Toate prinse din urm\u0103",
    back: "\u00cenapoi",
    backgroundSyncControlsVisibility: "Sincronizarea \u00een fundal controleaz\u0103 vizibilitatea",
    cached: "\u00cen cache",
    camera: "Camera foto",
    camerasOnline: "Camere online",
    genericCamera: "Camera foto",
    hlsPlaybackFailed: "Redarea HLS a e\u0219uat",
    hlsPlaybackUnsupported: "Redarea HLS nu este acceptat\u0103 de acest browser",
    lazyCacheOnPlayback: "Cache lene\u0219 la redare",
    loading: "\u00cenc\u0103rcare",
    loadingRecordings: "Se \u00eencarc\u0103 \u00eenregistr\u0103rile...",
    newestRecording: "Cea mai nou\u0103 \u00eenregistrare",
    noCameraSelected: "Nicio camer\u0103 nu a fost selectat\u0103",
    noCamerasFound: "Nu au fost g\u0103site camere",
    noCamerasFoundSentence: "Nu au fost g\u0103site camere.",
    noRecordingsForDate: "Nu exist\u0103 \u00eenregistr\u0103ri pentru aceast\u0103 dat\u0103.",
    noRecordingsReady: "Nicio \u00eenregistrare gata",
    noThumbnail: "F\u0103r\u0103 miniatur\u0103",
    noneYet: "Nici unul \u00eenc\u0103",
    notCached: "Nu este stocat \u00een cache",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Preg\u0103tirea",
    preparingRecording: "Se preg\u0103te\u0219te \u00eenregistrarea...",
    ready: "Gata",
    readyToWatch: "Gata de vizionat",
    recordingEmpty: "\u00cenregistrarea este goal\u0103",
    recordingIsNotReady: "\u00cenregistrarea nu este \u00eenc\u0103 gata.",
    recordingIsNotReadyStatus: "\u00cenregistrarea nu este gata ({status})",
    recordingsCountStatus: "{shown} din {total} \u00eenregistr\u0103ri - {state}",
    recordingsReady: "\u00cenregistr\u0103rile sunt gata",
    refresh: "Re\u00eemprosp\u0103ta\u021bi",
    selectRecordingToPlay: "Selecta\u021bi o \u00eenregistrare pentru redare",
    storageUsed: "Depozitare folosit\u0103",
    stillSyncing: "{count} \u00eenc\u0103 se sincronizeaz\u0103",
    couldNotLoadHlsPlayer: "Playerul HLS nu a putut fi \u00eenc\u0103rcat",
    date: "Data",
  },
  "ru": {
    allCamerasOffline: "\u0412\u0441\u0435 \u043a\u0430\u043c\u0435\u0440\u044b \u043e\u0444\u0444\u043b\u0430\u0439\u043d",
    allCamerasOnline: "\u0412\u0441\u0435 \u043a\u0430\u043c\u0435\u0440\u044b \u043e\u043d\u043b\u0430\u0439\u043d",
    allCaughtUp: "\u0412\u0441\u0435 \u0434\u043e\u0433\u043d\u0430\u043b\u0438",
    back: "\u041d\u0430\u0437\u0430\u0434",
    backgroundSyncControlsVisibility: "\u0424\u043e\u043d\u043e\u0432\u0430\u044f \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0438\u0440\u0443\u0435\u0442 \u0432\u0438\u0434\u0438\u043c\u043e\u0441\u0442\u044c",
    cached: "\u041a\u044d\u0448\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439",
    camera: "\u041a\u0430\u043c\u0435\u0440\u0430",
    camerasOnline: "\u041a\u0430\u043c\u0435\u0440\u044b \u043e\u043d\u043b\u0430\u0439\u043d",
    genericCamera: "\u041a\u0430\u043c\u0435\u0440\u0430",
    hlsPlaybackFailed: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0441\u0442\u0438 HLS.",
    hlsPlaybackUnsupported: "\u0412\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u0435 HLS \u043d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u044d\u0442\u0438\u043c \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u043e\u043c.",
    lazyCacheOnPlayback: "\u041b\u0435\u043d\u0438\u0432\u044b\u0439 \u043a\u0435\u0448 \u043f\u0440\u0438 \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u0438",
    loading: "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430",
    loadingRecordings: "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0435\u0439...",
    newestRecording: "\u041d\u043e\u0432\u0435\u0439\u0448\u0430\u044f \u0437\u0430\u043f\u0438\u0441\u044c",
    noCameraSelected: "\u041a\u0430\u043c\u0435\u0440\u0430 \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u0430",
    noCamerasFound: "\u041a\u0430\u043c\u0435\u0440\u044b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b",
    noCamerasFoundSentence: "\u041a\u0430\u043c\u0435\u0440\u044b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b.",
    noRecordingsForDate: "\u041d\u0430 \u044d\u0442\u0443 \u0434\u0430\u0442\u0443 \u043d\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0435\u0439.",
    noRecordingsReady: "\u041d\u0435\u0442 \u0433\u043e\u0442\u043e\u0432\u044b\u0445 \u0437\u0430\u043f\u0438\u0441\u0435\u0439",
    noThumbnail: "\u041d\u0435\u0442 \u043c\u0438\u043d\u0438\u0430\u0442\u044e\u0440\u044b",
    noneYet: "\u041f\u043e\u043a\u0430 \u043d\u0435\u0442",
    notCached: "\u041d\u0435 \u043a\u044d\u0448\u0438\u0440\u0443\u0435\u0442\u0441\u044f",
    offline: "\u043e\u0444\u043b\u0430\u0439\u043d",
    offlineCount: "{count} \u043e\u0444\u043b\u0430\u0439\u043d",
    online: "\u043e\u043d\u043b\u0430\u0439\u043d",
    preparing: "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430",
    preparingRecording: "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0438...",
    ready: "\u0413\u043e\u0442\u043e\u0432\u043e",
    readyToWatch: "\u0413\u043e\u0442\u043e\u0432 \u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c",
    recordingEmpty: "\u0417\u0430\u043f\u0438\u0441\u044c \u043f\u0443\u0441\u0442\u0430",
    recordingIsNotReady: "\u0417\u0430\u043f\u0438\u0441\u044c \u0435\u0449\u0435 \u043d\u0435 \u0433\u043e\u0442\u043e\u0432\u0430.",
    recordingIsNotReadyStatus: "\u0417\u0430\u043f\u0438\u0441\u044c \u043d\u0435 \u0433\u043e\u0442\u043e\u0432\u0430 ({status})",
    recordingsCountStatus: "{shown} \u0438\u0437 \u0437\u0430\u043f\u0438\u0441\u0435\u0439 {total}\u00a0\u2013 {state}",
    recordingsReady: "\u0417\u0430\u043f\u0438\u0441\u0438 \u0433\u043e\u0442\u043e\u0432\u044b",
    refresh: "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c",
    selectRecordingToPlay: "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0437\u0430\u043f\u0438\u0441\u044c \u0434\u043b\u044f \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u044f",
    storageUsed: "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c\u043e\u0435 \u0445\u0440\u0430\u043d\u0438\u043b\u0438\u0449\u0435",
    stillSyncing: "{count} \u0432\u0441\u0435 \u0435\u0449\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u0443\u0435\u0442\u0441\u044f",
    couldNotLoadHlsPlayer: "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043f\u0440\u043e\u0438\u0433\u0440\u044b\u0432\u0430\u0442\u0435\u043b\u044c HLS.",
    date: "\u0414\u0430\u0442\u0430",
  },
  "sk": {
    allCamerasOffline: "V\u0161etky kamery s\u00fa offline",
    allCamerasOnline: "V\u0161etky kamery online",
    allCaughtUp: "V\u0161etko dohnan\u00e9",
    back: "Sp\u00e4\u0165",
    backgroundSyncControlsVisibility: "Synchroniz\u00e1cia na pozad\u00ed ovl\u00e1da vidite\u013enos\u0165",
    cached: "Vo vyrovn\u00e1vacej pam\u00e4ti",
    camera: "Fotoapar\u00e1t",
    camerasOnline: "Kamery online",
    genericCamera: "Fotoapar\u00e1t",
    hlsPlaybackFailed: "Prehr\u00e1vanie HLS zlyhalo",
    hlsPlaybackUnsupported: "Prehr\u00e1vanie HLS tento prehliada\u010d nepodporuje",
    lazyCacheOnPlayback: "Leniv\u00e1 vyrovn\u00e1vacia pam\u00e4\u0165 pri prehr\u00e1van\u00ed",
    loading: "Na\u010d\u00edtava sa",
    loadingRecordings: "Na\u010d\u00edtavaj\u00fa sa nahr\u00e1vky...",
    newestRecording: "Najnov\u0161ia nahr\u00e1vka",
    noCameraSelected: "Nie je vybrat\u00e1 \u017eiadna kamera",
    noCamerasFound: "Nena\u0161li sa \u017eiadne kamery",
    noCamerasFoundSentence: "Nena\u0161li sa \u017eiadne kamery.",
    noRecordingsForDate: "Pre tento d\u00e1tum nie s\u00fa \u017eiadne nahr\u00e1vky.",
    noRecordingsReady: "Nie s\u00fa pripraven\u00e9 \u017eiadne nahr\u00e1vky",
    noThumbnail: "\u017diadna miniat\u00fara",
    noneYet: "Zatia\u013e \u017eiadne",
    notCached: "Neulo\u017een\u00e9 do vyrovn\u00e1vacej pam\u00e4te",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "Pr\u00edprava",
    preparingRecording: "Pripravuje sa nahr\u00e1vanie...",
    ready: "Pripraven\u00fd",
    readyToWatch: "Pripraven\u00e9 na pozeranie",
    recordingEmpty: "Nahr\u00e1vanie je pr\u00e1zdne",
    recordingIsNotReady: "Nahr\u00e1vanie e\u0161te nie je pripraven\u00e9.",
    recordingIsNotReadyStatus: "Nahr\u00e1vanie nie je pripraven\u00e9 ({status})",
    recordingsCountStatus: "{shown} nahr\u00e1vok {total} - {state}",
    recordingsReady: "Nahr\u00e1vky s\u00fa pripraven\u00e9",
    refresh: "Obnovi\u0165",
    selectRecordingToPlay: "Vyberte nahr\u00e1vku, ktor\u00fa chcete prehra\u0165",
    storageUsed: "Pou\u017eit\u00e9 \u00falo\u017eisko",
    stillSyncing: "{count} sa st\u00e1le synchronizuje",
    couldNotLoadHlsPlayer: "Prehr\u00e1va\u010d HLS sa nepodarilo na\u010d\u00edta\u0165",
    date: "D\u00e1tum",
  },
  "sl": {
    allCamerasOffline: "Vse kamere brez povezave",
    allCamerasOnline: "Vse kamere na spletu",
    allCaughtUp: "Vse dohitelo",
    back: "Nazaj",
    backgroundSyncControlsVisibility: "Sinhronizacija v ozadju nadzira vidnost",
    cached: "Predpomnjeno",
    camera: "Kamera",
    camerasOnline: "Kamere na spletu",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "Predvajanje HLS ni uspelo",
    hlsPlaybackUnsupported: "Ta brskalnik ne podpira predvajanja HLS",
    lazyCacheOnPlayback: "Leni predpomnilnik pri predvajanju",
    loading: "Nalaganje",
    loadingRecordings: "Nalaganje posnetkov ...",
    newestRecording: "Najnovej\u0161i posnetek",
    noCameraSelected: "Izbrana ni nobena kamera",
    noCamerasFound: "Najdena ni bila nobena kamera",
    noCamerasFoundSentence: "Najdena ni bila nobena kamera.",
    noRecordingsForDate: "Za ta datum ni posnetkov.",
    noRecordingsReady: "Ni pripravljenih posnetkov",
    noThumbnail: "Brez sli\u010dice",
    noneYet: "Nobenega \u0161e",
    notCached: "Ni predpomnjeno",
    offline: "brez povezave",
    offlineCount: "{count} brez povezave",
    online: "na spletu",
    preparing: "Priprava",
    preparingRecording: "Priprava snemanja ...",
    ready: "pripravljena",
    readyToWatch: "Pripravljen za ogled",
    recordingEmpty: "Posnetek je prazen",
    recordingIsNotReady: "Posnetek \u0161e ni pripravljen.",
    recordingIsNotReadyStatus: "Posnetek ni pripravljen ({status})",
    recordingsCountStatus: "{shown} od {total} posnetkov - {state}",
    recordingsReady: "Posnetki so pripravljeni",
    refresh: "Osve\u017ei",
    selectRecordingToPlay: "Izberite posnetek za predvajanje",
    storageUsed: "Uporabljen prostor za shranjevanje",
    stillSyncing: "{count} se \u0161e vedno sinhronizira",
    couldNotLoadHlsPlayer: "Predvajalnika HLS ni bilo mogo\u010de nalo\u017eiti",
    date: "Datum",
  },
  "sv": {
    allCamerasOffline: "Alla kameror offline",
    allCamerasOnline: "Alla kameror online",
    allCaughtUp: "Alla kom ikapp",
    back: "Tillbaka",
    backgroundSyncControlsVisibility: "Bakgrundssynkronisering styr synligheten",
    cached: "Cachad",
    camera: "Kamera",
    camerasOnline: "Kameror online",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS uppspelning misslyckades",
    hlsPlaybackUnsupported: "HLS-uppspelning st\u00f6ds inte av den h\u00e4r webbl\u00e4saren",
    lazyCacheOnPlayback: "Lat cache vid uppspelning",
    loading: "Laddar",
    loadingRecordings: "Laddar inspelningar...",
    newestRecording: "Nyaste inspelningen",
    noCameraSelected: "Ingen kamera har valts",
    noCamerasFound: "Inga kameror hittades",
    noCamerasFoundSentence: "Inga kameror hittades.",
    noRecordingsForDate: "Inga inspelningar f\u00f6r detta datum.",
    noRecordingsReady: "Inga inspelningar klara",
    noThumbnail: "Ingen miniatyrbild",
    noneYet: "Inga \u00e4nnu",
    notCached: "Ej cachad",
    offline: "offline",
    offlineCount: "{count} offline",
    online: "online",
    preparing: "F\u00f6rbereder",
    preparingRecording: "F\u00f6rbereder inspelning...",
    ready: "Klar",
    readyToWatch: "Redo att titta",
    recordingEmpty: "Inspelningen \u00e4r tom",
    recordingIsNotReady: "Inspelningen \u00e4r inte klar \u00e4nnu.",
    recordingIsNotReadyStatus: "Inspelningen \u00e4r inte klar ({status})",
    recordingsCountStatus: "{shown} av {total}-inspelningar - {state}",
    recordingsReady: "Inspelningarna \u00e4r klara",
    refresh: "Uppdatera",
    selectRecordingToPlay: "V\u00e4lj en inspelning att spela upp",
    storageUsed: "F\u00f6rvaring anv\u00e4nds",
    stillSyncing: "{count} synkroniserar fortfarande",
    couldNotLoadHlsPlayer: "Det gick inte att ladda HLS-spelaren",
    date: "Datum",
  },
  "th": {
    allCamerasOffline: "\u0e01\u0e25\u0e49\u0e2d\u0e07\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14\u0e2d\u0e2d\u0e1f\u0e44\u0e25\u0e19\u0e4c",
    allCamerasOnline: "\u0e01\u0e25\u0e49\u0e2d\u0e07\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14\u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c",
    allCaughtUp: "\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14\u0e15\u0e32\u0e21\u0e17\u0e31\u0e19",
    back: "\u0e01\u0e25\u0e31\u0e1a",
    backgroundSyncControlsVisibility: "\u0e01\u0e32\u0e23\u0e0b\u0e34\u0e07\u0e04\u0e4c\u0e1e\u0e37\u0e49\u0e19\u0e2b\u0e25\u0e31\u0e07\u0e04\u0e27\u0e1a\u0e04\u0e38\u0e21\u0e01\u0e32\u0e23\u0e21\u0e2d\u0e07\u0e40\u0e2b\u0e47\u0e19",
    cached: "\u0e41\u0e04\u0e0a",
    camera: "\u0e01\u0e25\u0e49\u0e2d\u0e07",
    camerasOnline: "\u0e01\u0e25\u0e49\u0e2d\u0e07\u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c",
    genericCamera: "\u0e01\u0e25\u0e49\u0e2d\u0e07",
    hlsPlaybackFailed: "\u0e01\u0e32\u0e23\u0e40\u0e25\u0e48\u0e19 HLS \u0e25\u0e49\u0e21\u0e40\u0e2b\u0e25\u0e27",
    hlsPlaybackUnsupported: "\u0e40\u0e1a\u0e23\u0e32\u0e27\u0e4c\u0e40\u0e0b\u0e2d\u0e23\u0e4c\u0e19\u0e35\u0e49\u0e44\u0e21\u0e48\u0e23\u0e2d\u0e07\u0e23\u0e31\u0e1a\u0e01\u0e32\u0e23\u0e40\u0e25\u0e48\u0e19 HLS",
    lazyCacheOnPlayback: "\u0e41\u0e04\u0e0a\u0e02\u0e35\u0e49\u0e40\u0e01\u0e35\u0e22\u0e08\u0e43\u0e19\u0e01\u0e32\u0e23\u0e40\u0e25\u0e48\u0e19",
    loading: "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e42\u0e2b\u0e25\u0e14",
    loadingRecordings: "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e42\u0e2b\u0e25\u0e14\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01...",
    newestRecording: "\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e43\u0e2b\u0e21\u0e48\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14",
    noCameraSelected: "\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e01\u0e25\u0e49\u0e2d\u0e07",
    noCamerasFound: "\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e01\u0e25\u0e49\u0e2d\u0e07",
    noCamerasFoundSentence: "\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e01\u0e25\u0e49\u0e2d\u0e07",
    noRecordingsForDate: "\u0e44\u0e21\u0e48\u0e21\u0e35\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e27\u0e31\u0e19\u0e17\u0e35\u0e48\u0e19\u0e35\u0e49",
    noRecordingsReady: "\u0e44\u0e21\u0e48\u0e21\u0e35\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e17\u0e35\u0e48\u0e1e\u0e23\u0e49\u0e2d\u0e21",
    noThumbnail: "\u0e44\u0e21\u0e48\u0e21\u0e35\u0e20\u0e32\u0e1e\u0e02\u0e19\u0e32\u0e14\u0e22\u0e48\u0e2d",
    noneYet: "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35",
    notCached: "\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e41\u0e04\u0e0a",
    offline: "\u0e2d\u0e2d\u0e1f\u0e44\u0e25\u0e19\u0e4c",
    offlineCount: "{count} \u0e2d\u0e2d\u0e1f\u0e44\u0e25\u0e19\u0e4c",
    online: "\u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c",
    preparing: "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e40\u0e15\u0e23\u0e35\u0e22\u0e21\u0e15\u0e31\u0e27",
    preparingRecording: "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e40\u0e15\u0e23\u0e35\u0e22\u0e21\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01...",
    ready: "\u0e1e\u0e23\u0e49\u0e2d\u0e21",
    readyToWatch: "\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e23\u0e31\u0e1a\u0e0a\u0e21",
    recordingEmpty: "\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e27\u0e48\u0e32\u0e07\u0e40\u0e1b\u0e25\u0e48\u0e32",
    recordingIsNotReady: "\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e1e\u0e23\u0e49\u0e2d\u0e21",
    recordingIsNotReadyStatus: "\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e44\u0e21\u0e48\u0e1e\u0e23\u0e49\u0e2d\u0e21 ({status})",
    recordingsCountStatus: "{shown} \u0e02\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01 {total} - {state}",
    recordingsReady: "\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e41\u0e25\u0e49\u0e27",
    refresh: "\u0e23\u0e35\u0e40\u0e1f\u0e23\u0e0a",
    selectRecordingToPlay: "\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e01\u0e32\u0e23\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e17\u0e35\u0e48\u0e08\u0e30\u0e40\u0e25\u0e48\u0e19",
    storageUsed: "\u0e1e\u0e37\u0e49\u0e19\u0e17\u0e35\u0e48\u0e40\u0e01\u0e47\u0e1a\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e17\u0e35\u0e48\u0e43\u0e0a\u0e49",
    stillSyncing: "{count} \u0e22\u0e31\u0e07\u0e04\u0e07\u0e0b\u0e34\u0e07\u0e04\u0e4c\u0e2d\u0e22\u0e39\u0e48",
    couldNotLoadHlsPlayer: "\u0e44\u0e21\u0e48\u0e2a\u0e32\u0e21\u0e32\u0e23\u0e16\u0e42\u0e2b\u0e25\u0e14\u0e40\u0e04\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e40\u0e25\u0e48\u0e19 HLS",
    date: "\u0e27\u0e31\u0e19\u0e17\u0e35\u0e48",
  },
  "tr": {
    allCamerasOffline: "T\u00fcm kameralar \u00e7evrimd\u0131\u015f\u0131",
    allCamerasOnline: "T\u00fcm kameralar \u00e7evrimi\u00e7i",
    allCaughtUp: "Hepsi yakaland\u0131",
    back: "Geri",
    backgroundSyncControlsVisibility: "Arka planda senkronizasyon g\u00f6r\u00fcn\u00fcrl\u00fc\u011f\u00fc kontrol eder",
    cached: "\u00d6nbelle\u011fe al\u0131nd\u0131",
    camera: "Kamera",
    camerasOnline: "\u00c7evrimi\u00e7i Kameralar",
    genericCamera: "Kamera",
    hlsPlaybackFailed: "HLS oynatma ba\u015far\u0131s\u0131z oldu",
    hlsPlaybackUnsupported: "HLS oynatma bu taray\u0131c\u0131 taraf\u0131ndan desteklenmiyor",
    lazyCacheOnPlayback: "Oynatmada tembel \u00f6nbellek",
    loading: "Y\u00fckleniyor",
    loadingRecordings: "Kay\u0131tlar y\u00fckleniyor...",
    newestRecording: "En Yeni Kay\u0131t",
    noCameraSelected: "Kamera se\u00e7ilmedi",
    noCamerasFound: "Kamera bulunamad\u0131",
    noCamerasFoundSentence: "Kamera bulunamad\u0131.",
    noRecordingsForDate: "Bu tarihe ait kay\u0131t yok.",
    noRecordingsReady: "Haz\u0131r kay\u0131t yok",
    noThumbnail: "K\u00fc\u00e7\u00fck resim yok",
    noneYet: "Hen\u00fcz yok",
    notCached: "\u00d6nbelle\u011fe al\u0131nmad\u0131",
    offline: "\u00e7evrimd\u0131\u015f\u0131",
    offlineCount: "{count} \u00e7evrimd\u0131\u015f\u0131",
    online: "\u00e7evrimi\u00e7i",
    preparing: "Haz\u0131rlan\u0131yor",
    preparingRecording: "Kay\u0131t haz\u0131rlan\u0131yor...",
    ready: "Haz\u0131r",
    readyToWatch: "\u0130zlemeye Haz\u0131r",
    recordingEmpty: "Kay\u0131t bo\u015f",
    recordingIsNotReady: "Kay\u0131t hen\u00fcz haz\u0131r de\u011fil.",
    recordingIsNotReadyStatus: "Kay\u0131t haz\u0131r de\u011fil ({status})",
    recordingsCountStatus: "{total} kay\u0131tlar\u0131n\u0131n {shown}'\u0131 - {state}",
    recordingsReady: "Kay\u0131tlar haz\u0131r",
    refresh: "Yenile",
    selectRecordingToPlay: "Oynat\u0131lacak bir kay\u0131t se\u00e7in",
    storageUsed: "Kullan\u0131lan Depolama",
    stillSyncing: "{count} h\u00e2l\u00e2 senkronize ediliyor",
    couldNotLoadHlsPlayer: "HLS oynat\u0131c\u0131s\u0131 y\u00fcklenemedi",
    date: "Tarih",
  },
  "uk": {
    allCamerasOffline: "\u0423\u0441\u0456 \u043a\u0430\u043c\u0435\u0440\u0438 \u043e\u0444\u043b\u0430\u0439\u043d",
    allCamerasOnline: "\u0412\u0441\u0456 \u043a\u0430\u043c\u0435\u0440\u0438 \u043e\u043d\u043b\u0430\u0439\u043d",
    allCaughtUp: "\u0412\u0441\u0435 \u043d\u0430\u0437\u0434\u043e\u0433\u043d\u0430\u043b\u0438",
    back: "\u041d\u0430\u0437\u0430\u0434",
    backgroundSyncControlsVisibility: "\u0424\u043e\u043d\u043e\u0432\u0430 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0456\u0437\u0430\u0446\u0456\u044f \u043a\u0435\u0440\u0443\u0454 \u0432\u0438\u0434\u0438\u043c\u0456\u0441\u0442\u044e",
    cached: "\u041a\u0435\u0448\u043e\u0432\u0430\u043d\u043e",
    camera: "\u041a\u0430\u043c\u0435\u0440\u0430",
    camerasOnline: "\u041a\u0430\u043c\u0435\u0440\u0438 \u043e\u043d\u043b\u0430\u0439\u043d",
    genericCamera: "\u041a\u0430\u043c\u0435\u0440\u0430",
    hlsPlaybackFailed: "\u041f\u043e\u043c\u0438\u043b\u043a\u0430 \u0432\u0456\u0434\u0442\u0432\u043e\u0440\u0435\u043d\u043d\u044f HLS",
    hlsPlaybackUnsupported: "\u0412\u0456\u0434\u0442\u0432\u043e\u0440\u0435\u043d\u043d\u044f HLS \u043d\u0435 \u043f\u0456\u0434\u0442\u0440\u0438\u043c\u0443\u0454\u0442\u044c\u0441\u044f \u0446\u0438\u043c \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u043e\u043c",
    lazyCacheOnPlayback: "\u0412\u0456\u0434\u043a\u043b\u0430\u0434\u0435\u043d\u0438\u0439 \u043a\u0435\u0448 \u043f\u0456\u0434 \u0447\u0430\u0441 \u0432\u0456\u0434\u0442\u0432\u043e\u0440\u0435\u043d\u043d\u044f",
    loading: "\u0417\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043d\u044f",
    loadingRecordings: "\u0417\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043d\u044f \u0437\u0430\u043f\u0438\u0441\u0456\u0432...",
    newestRecording: "\u041d\u0430\u0439\u043d\u043e\u0432\u0456\u0448\u0438\u0439 \u0437\u0430\u043f\u0438\u0441",
    noCameraSelected: "\u041a\u0430\u043c\u0435\u0440\u0430 \u043d\u0435 \u0432\u0438\u0431\u0440\u0430\u043d\u0430",
    noCamerasFound: "\u041a\u0430\u043c\u0435\u0440\u0438 \u043d\u0435 \u0437\u043d\u0430\u0439\u0434\u0435\u043d\u043e",
    noCamerasFoundSentence: "\u041a\u0430\u043c\u0435\u0440\u0438 \u043d\u0435 \u0437\u043d\u0430\u0439\u0434\u0435\u043d\u043e.",
    noRecordingsForDate: "\u041d\u0435\u043c\u0430\u0454 \u0437\u0430\u043f\u0438\u0441\u0456\u0432 \u043d\u0430 \u0446\u044e \u0434\u0430\u0442\u0443.",
    noRecordingsReady: "\u041d\u0435\u043c\u0430\u0454 \u0433\u043e\u0442\u043e\u0432\u0438\u0445 \u0437\u0430\u043f\u0438\u0441\u0456\u0432",
    noThumbnail: "\u0411\u0435\u0437 \u043c\u0456\u043d\u0456\u0430\u0442\u044e\u0440\u0438",
    noneYet: "\u041f\u043e\u043a\u0438 \u043d\u0435\u043c\u0430\u0454",
    notCached: "\u041d\u0435 \u043a\u0435\u0448\u0443\u0454\u0442\u044c\u0441\u044f",
    offline: "\u043e\u0444\u043b\u0430\u0439\u043d",
    offlineCount: "{count} \u043e\u0444\u043b\u0430\u0439\u043d",
    online: "\u043e\u043d\u043b\u0430\u0439\u043d",
    preparing: "\u0413\u043e\u0442\u0443\u0454\u0442\u044c\u0441\u044f",
    preparingRecording: "\u041f\u0456\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0443...",
    ready: "\u0413\u043e\u0442\u043e\u0432\u0438\u0439",
    readyToWatch: "\u0413\u043e\u0442\u043e\u0432\u0438\u0439 \u0434\u043e \u043f\u0435\u0440\u0435\u0433\u043b\u044f\u0434\u0443",
    recordingEmpty: "\u0417\u0430\u043f\u0438\u0441 \u043f\u043e\u0440\u043e\u0436\u043d\u0456\u0439",
    recordingIsNotReady: "\u0417\u0430\u043f\u0438\u0441 \u0449\u0435 \u043d\u0435 \u0433\u043e\u0442\u043e\u0432\u0438\u0439.",
    recordingIsNotReadyStatus: "\u0417\u0430\u043f\u0438\u0441 \u043d\u0435 \u0433\u043e\u0442\u043e\u0432\u0438\u0439 ({status})",
    recordingsCountStatus: "{shown} \u0456\u0437 {total} \u0437\u0430\u043f\u0438\u0441\u0456\u0432 - {state}",
    recordingsReady: "\u0417\u0430\u043f\u0438\u0441\u0438 \u0433\u043e\u0442\u043e\u0432\u0456",
    refresh: "\u041e\u043d\u043e\u0432\u0438\u0442\u0438",
    selectRecordingToPlay: "\u0412\u0438\u0431\u0435\u0440\u0456\u0442\u044c \u0437\u0430\u043f\u0438\u0441 \u0434\u043b\u044f \u0432\u0456\u0434\u0442\u0432\u043e\u0440\u0435\u043d\u043d\u044f",
    storageUsed: "\u041f\u0430\u043c'\u044f\u0442\u044c \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u043e",
    stillSyncing: "{count} \u0432\u0441\u0435 \u0449\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0456\u0437\u0443\u0454\u0442\u044c\u0441\u044f",
    couldNotLoadHlsPlayer: "\u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0438\u0442\u0438 \u043f\u043b\u0435\u0454\u0440 HLS",
    date: "\u0414\u0430\u0442\u0430",
  },
  "vi": {
    allCamerasOffline: "T\u1ea5t c\u1ea3 camera ngo\u1ea1i tuy\u1ebfn",
    allCamerasOnline: "T\u1ea5t c\u1ea3 c\u00e1c m\u00e1y \u1ea3nh tr\u1ef1c tuy\u1ebfn",
    allCaughtUp: "T\u1ea5t c\u1ea3 \u0111\u00e3 b\u1eaft k\u1ecbp",
    back: "Quay l\u1ea1i",
    backgroundSyncControlsVisibility: "\u0110\u1ed3ng b\u1ed9 h\u00f3a n\u1ec1n ki\u1ec3m so\u00e1t kh\u1ea3 n\u0103ng hi\u1ec3n th\u1ecb",
    cached: "\u0110\u00e3 l\u01b0u v\u00e0o b\u1ed9 nh\u1edb \u0111\u1ec7m",
    camera: "M\u00e1y \u1ea3nh",
    camerasOnline: "M\u00e1y \u1ea3nh tr\u1ef1c tuy\u1ebfn",
    genericCamera: "M\u00e1y \u1ea3nh",
    hlsPlaybackFailed: "Ph\u00e1t l\u1ea1i HLS kh\u00f4ng th\u00e0nh c\u00f4ng",
    hlsPlaybackUnsupported: "Tr\u00ecnh duy\u1ec7t n\u00e0y kh\u00f4ng h\u1ed7 tr\u1ee3 ph\u00e1t l\u1ea1i HLS",
    lazyCacheOnPlayback: "B\u1ed9 nh\u1edb \u0111\u1ec7m l\u01b0\u1eddi bi\u1ebfng khi ph\u00e1t l\u1ea1i",
    loading: "\u0110ang t\u1ea3i",
    loadingRecordings: "\u0110ang t\u1ea3i b\u1ea3n ghi...",
    newestRecording: "Ghi \u00e2m m\u1edbi nh\u1ea5t",
    noCameraSelected: "Kh\u00f4ng c\u00f3 m\u00e1y \u1ea3nh n\u00e0o \u0111\u01b0\u1ee3c ch\u1ecdn",
    noCamerasFound: "Kh\u00f4ng t\u00ecm th\u1ea5y m\u00e1y \u1ea3nh n\u00e0o",
    noCamerasFoundSentence: "Kh\u00f4ng t\u00ecm th\u1ea5y m\u00e1y \u1ea3nh.",
    noRecordingsForDate: "Kh\u00f4ng c\u00f3 b\u1ea3n ghi n\u00e0o cho ng\u00e0y n\u00e0y.",
    noRecordingsReady: "Ch\u01b0a c\u00f3 b\u1ea3n ghi n\u00e0o s\u1eb5n s\u00e0ng",
    noThumbnail: "Kh\u00f4ng c\u00f3 h\u00ecnh thu nh\u1ecf",
    noneYet: "Ch\u01b0a c\u00f3",
    notCached: "Kh\u00f4ng \u0111\u01b0\u1ee3c l\u01b0u v\u00e0o b\u1ed9 nh\u1edb \u0111\u1ec7m",
    offline: "ngo\u1ea1i tuy\u1ebfn",
    offlineCount: "{count} ngo\u1ea1i tuy\u1ebfn",
    online: "tr\u1ef1c tuy\u1ebfn",
    preparing: "chu\u1ea9n b\u1ecb",
    preparingRecording: "\u0110ang chu\u1ea9n b\u1ecb ghi \u00e2m...",
    ready: "S\u1eb5n s\u00e0ng",
    readyToWatch: "S\u1eb5n s\u00e0ng \u0111\u1ec3 xem",
    recordingEmpty: "B\u1ea3n ghi tr\u1ed1ng",
    recordingIsNotReady: "Vi\u1ec7c ghi \u00e2m v\u1eabn ch\u01b0a s\u1eb5n s\u00e0ng.",
    recordingIsNotReadyStatus: "Qu\u00e1 tr\u00ecnh ghi ch\u01b0a s\u1eb5n s\u00e0ng ({status})",
    recordingsCountStatus: "{shown} c\u1ee7a b\u1ea3n ghi {total} - {state}",
    recordingsReady: "B\u1ea3n ghi \u0111\u00e3 s\u1eb5n s\u00e0ng",
    refresh: "L\u00e0m m\u1edbi",
    selectRecordingToPlay: "Ch\u1ecdn b\u1ea3n ghi \u0111\u1ec3 ph\u00e1t",
    storageUsed: "B\u1ed9 nh\u1edb \u0111\u00e3 s\u1eed d\u1ee5ng",
    stillSyncing: "{count} v\u1eabn \u0111ang \u0111\u1ed3ng b\u1ed9 h\u00f3a",
    couldNotLoadHlsPlayer: "Kh\u00f4ng th\u1ec3 t\u1ea3i tr\u00ecnh ph\u00e1t HLS",
    date: "Ng\u00e0y",
  },
  "zh-CN": {
    allCamerasOffline: "\u6240\u6709\u6444\u50cf\u673a\u79bb\u7ebf",
    allCamerasOnline: "\u6240\u6709\u6444\u50cf\u673a\u5728\u7ebf",
    allCaughtUp: "\u5168\u90e8\u90fd\u8ffd\u4e0a\u4e86",
    back: "\u8fd4\u56de",
    backgroundSyncControlsVisibility: "\u540e\u53f0\u540c\u6b65\u63a7\u5236\u53ef\u89c1\u6027",
    cached: "\u7f13\u5b58",
    camera: "\u76f8\u673a",
    camerasOnline: "\u5728\u7ebf\u76f8\u673a",
    genericCamera: "\u76f8\u673a",
    hlsPlaybackFailed: "HLS \u64ad\u653e\u5931\u8d25",
    hlsPlaybackUnsupported: "\u8be5\u6d4f\u89c8\u5668\u4e0d\u652f\u6301 HLS \u64ad\u653e",
    lazyCacheOnPlayback: "\u64ad\u653e\u65f6\u5ef6\u8fdf\u7f13\u5b58",
    loading: "\u52a0\u8f7d\u4e2d",
    loadingRecordings: "\u6b63\u5728\u52a0\u8f7d\u5f55\u97f3...",
    newestRecording: "\u6700\u65b0\u5f55\u97f3",
    noCameraSelected: "\u672a\u9009\u62e9\u76f8\u673a",
    noCamerasFound: "\u6ca1\u6709\u627e\u5230\u76f8\u673a",
    noCamerasFoundSentence: "\u6ca1\u6709\u627e\u5230\u76f8\u673a\u3002",
    noRecordingsForDate: "\u8be5\u65e5\u671f\u6ca1\u6709\u5f55\u97f3\u3002",
    noRecordingsReady: "\u6ca1\u6709\u51c6\u5907\u597d\u5f55\u97f3",
    noThumbnail: "\u65e0\u7f29\u7565\u56fe",
    noneYet: "\u8fd8\u6ca1\u6709",
    notCached: "\u672a\u7f13\u5b58",
    offline: "\u79bb\u7ebf",
    offlineCount: "{count} \u79bb\u7ebf",
    online: "\u5728\u7ebf",
    preparing: "\u51c6\u5907\u4e2d",
    preparingRecording: "\u51c6\u5907\u5f55\u97f3...",
    ready: "\u51c6\u5907\u597d",
    readyToWatch: "\u51c6\u5907\u89c2\u770b",
    recordingEmpty: "\u5f55\u97f3\u4e3a\u7a7a",
    recordingIsNotReady: "\u5f55\u97f3\u5c1a\u672a\u51c6\u5907\u597d\u3002",
    recordingIsNotReadyStatus: "\u5f55\u97f3\u5c1a\u672a\u51c6\u5907\u597d ({status})",
    recordingsCountStatus: "{total} \u5f55\u97f3\u4e2d\u7684 {shown} - {state}",
    recordingsReady: "\u5f55\u97f3\u5df2\u51c6\u5907\u597d",
    refresh: "\u5237\u65b0",
    selectRecordingToPlay: "\u9009\u62e9\u8981\u64ad\u653e\u7684\u5f55\u97f3",
    storageUsed: "\u5df2\u7528\u5b58\u50a8\u7a7a\u95f4",
    stillSyncing: "{count} \u4ecd\u5728\u540c\u6b65",
    couldNotLoadHlsPlayer: "\u65e0\u6cd5\u52a0\u8f7d HLS \u64ad\u653e\u5668",
    date: "\u65e5\u671f",
  },
  "zh-TW": {
    allCamerasOffline: "\u6240\u6709\u651d\u5f71\u6a5f\u96e2\u7dda",
    allCamerasOnline: "\u6240\u6709\u651d\u5f71\u6a5f\u5728\u7dda",
    allCaughtUp: "\u5168\u90e8\u90fd\u8ffd\u4e0a\u4e86",
    back: "\u8fd4\u56de",
    backgroundSyncControlsVisibility: "\u5f8c\u53f0\u540c\u6b65\u63a7\u5236\u53ef\u898b\u6027",
    cached: "\u5feb\u53d6",
    camera: "\u76f8\u6a5f",
    camerasOnline: "\u7dda\u4e0a\u76f8\u6a5f",
    genericCamera: "\u76f8\u6a5f",
    hlsPlaybackFailed: "HLS \u64ad\u653e\u5931\u6557",
    hlsPlaybackUnsupported: "\u6b64\u700f\u89bd\u5668\u4e0d\u652f\u63f4 HLS \u64ad\u653e",
    lazyCacheOnPlayback: "\u64ad\u653e\u6642\u5ef6\u9072\u7de9\u5b58",
    loading: "\u8f09\u5165\u4e2d",
    loadingRecordings: "\u6b63\u5728\u8f09\u5165\u9304\u97f3...",
    newestRecording: "\u6700\u65b0\u9304\u97f3",
    noCameraSelected: "\u672a\u9078\u64c7\u76f8\u6a5f",
    noCamerasFound: "\u6c92\u6709\u627e\u5230\u76f8\u6a5f",
    noCamerasFoundSentence: "\u6c92\u6709\u627e\u5230\u76f8\u6a5f\u3002",
    noRecordingsForDate: "\u8a72\u65e5\u671f\u6c92\u6709\u9304\u97f3\u3002",
    noRecordingsReady: "\u6c92\u6709\u6e96\u5099\u597d\u9304\u97f3",
    noThumbnail: "\u7121\u7e2e\u5716",
    noneYet: "\u9084\u6c92\u6709",
    notCached: "\u672a\u5feb\u53d6",
    offline: "\u96e2\u7dda",
    offlineCount: "{count} \u96e2\u7dda",
    online: "\u7db2\u8def",
    preparing: "\u6e96\u5099\u4e2d",
    preparingRecording: "\u6e96\u5099\u9304\u97f3...",
    ready: "\u6e96\u5099\u597d",
    readyToWatch: "\u6e96\u5099\u89c0\u770b",
    recordingEmpty: "\u9304\u97f3\u70ba\u7a7a",
    recordingIsNotReady: "\u9304\u97f3\u5c1a\u672a\u6e96\u5099\u597d\u3002",
    recordingIsNotReadyStatus: "\u9304\u97f3\u5c1a\u672a\u6e96\u5099\u597d ({status})",
    recordingsCountStatus: "{total} \u9304\u97f3\u4e2d\u7684 {shown} - {state}",
    recordingsReady: "\u9304\u97f3\u5df2\u6e96\u5099\u597d",
    refresh: "\u91cd\u65b0\u6574\u7406",
    selectRecordingToPlay: "\u9078\u64c7\u8981\u64ad\u653e\u7684\u9304\u97f3",
    storageUsed: "\u5df2\u7528\u5132\u5b58\u7a7a\u9593",
    stillSyncing: "{count} \u4ecd\u5728\u540c\u6b65",
    couldNotLoadHlsPlayer: "\u7121\u6cd5\u8f09\u5165 HLS \u64ad\u653e\u5668",
    date: "\u65e5\u671f",
  },
};

const LANGUAGE_ALIASES = {
  "nb": "no",
  "nb-no": "no",
  "nn": "no",
  "nn-no": "no",
  "pt-br": "pt-BR",
  "zh-cn": "zh-CN",
  "zh-hans": "zh-CN",
  "zh-tw": "zh-TW",
  "zh-hant": "zh-TW",
};

class XSenseRecordingsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.data = null;
    this.selectedCameraKey = "";
    this.selectedDate = "";
    this.selectedClip = null;
    this.loading = false;
    this.error = "";
    this.signedPaths = new Map();
    this.playbackUrls = new Map();
    this.playbackTypes = new Map();
    this.playbackErrors = new Map();
    this.playbackLoadingKey = "";
    this.hlsInstances = new Map();
    this.hlsLibraryPromise = null;
    this.handleRouteChange = async () => {
      this.syncRouteFromHash();
      if (this.selectedClip) {
        await this.prepareClipPlayback(this.selectedClip);
      }
      this.render();
    };
  }

  set hass(value) {
    this._hass = value;
    if (!this.data && !this.loading) {
      this.loadData();
    }
  }

  connectedCallback() {
    window.addEventListener("hashchange", this.handleRouteChange);
    window.addEventListener("popstate", this.handleRouteChange);
    this.syncRouteFromHash();
    this.render();
  }

  disconnectedCallback() {
    window.removeEventListener("hashchange", this.handleRouteChange);
    window.removeEventListener("popstate", this.handleRouteChange);
    this.disposePlaybackResources();
  }

  async loadData() {
    if (!this._hass) return;
    this.loading = true;
    this.error = "";
    this.render();
    try {
      const data = await this._hass.callApi("GET", "xsense/recordings/panel");
      this.data = data;
      const cameras = data.cameras || [];
      if (!this.selectedCameraKey || !cameras.some((camera) => this.cameraKey(camera) === this.selectedCameraKey)) {
        this.selectedCameraKey = cameras[0] ? this.cameraKey(cameras[0]) : "";
      }
      const camera = this.camera;
      if (!this.selectedDate || !camera?.dates?.includes(this.selectedDate)) {
        this.selectedDate = camera?.dates?.[0] || "";
      }
      this.syncRouteFromHash();
      await this.signVisibleThumbnails();
      if (this.selectedClip) {
        await this.prepareClipPlayback(this.selectedClip);
      }
    } catch (err) {
      this.error = err?.message || String(err);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  get camera() {
    return (this.data?.cameras || []).find((camera) => this.cameraKey(camera) === this.selectedCameraKey);
  }

  get clips() {
    const camera = this.camera;
    if (!camera) return [];
    return (camera.clips || []).filter((clip) => clip.date === this.selectedDate);
  }

  render() {
    const cameras = this.data?.cameras || [];
    const camera = this.camera;
    const clips = this.clips;
    const clipCount = clips.length;
    const viewerClip = this.selectedClip && (this.findClip(this.selectedClip.entry_id, this.selectedClip.serial, this.selectedClip.start, this.selectedClip.end) || this.selectedClip);
    const useViewerPage = Boolean(viewerClip);
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100vh;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          box-sizing: border-box;
          font-family: var(--paper-font-body1_-_font-family, Roboto, Arial, sans-serif);
        }
        * { box-sizing: border-box; }
        .page {
          max-width: 1400px;
          margin: 0 auto;
          padding: 16px;
        }
        .toolbar {
          display: grid;
          grid-template-columns: minmax(180px, 260px) minmax(150px, 220px) 1fr auto;
          gap: 12px;
          align-items: end;
          margin-bottom: 16px;
        }
        label {
          display: grid;
          gap: 6px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        select, button {
          height: 40px;
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }
        select { padding: 0 10px; }
        button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 0 14px;
          cursor: pointer;
        }
        button:hover { background: var(--secondary-background-color); }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(150px, 1fr));
          gap: 10px;
          margin-bottom: 14px;
        }
        .stat-card {
          min-height: 78px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          padding: 10px 12px;
          display: grid;
          align-content: center;
          gap: 5px;
        }
        .stat-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .stat-value {
          color: var(--primary-text-color);
          font-size: 22px;
          line-height: 1.1;
          font-weight: 500;
        }
        .stat-sub {
          color: var(--secondary-text-color);
          font-size: 12px;
          line-height: 1.3;
          overflow-wrap: anywhere;
        }
        .status {
          min-height: 40px;
          display: flex;
          align-items: center;
          color: var(--secondary-text-color);
          font-size: 14px;
        }
        .clips {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
          gap: 10px;
        }
        .clip {
          display: grid;
          grid-template-rows: auto 1fr;
          min-height: 188px;
          overflow: hidden;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          cursor: pointer;
          text-align: left;
          padding: 0;
          font: inherit;
        }
        .thumb {
          position: relative;
          aspect-ratio: 16 / 9;
          background: var(--secondary-background-color);
          overflow: hidden;
        }
        .thumb img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }
        .missing-thumb {
          width: 100%;
          height: 100%;
          display: grid;
          place-items: center;
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .badge {
          position: absolute;
          right: 8px;
          bottom: 8px;
          padding: 3px 7px;
          border-radius: 5px;
          background: rgba(0, 0, 0, 0.72);
          color: #fff;
          font-size: 12px;
        }
        .meta {
          display: grid;
          gap: 4px;
          padding: 10px;
        }
        .title {
          font-size: 14px;
          line-height: 1.25;
          color: var(--primary-text-color);
          overflow-wrap: anywhere;
        }
        .sub {
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        .viewer {
          display: grid;
          gap: 12px;
          max-width: 1100px;
          margin: 0 auto;
        }
        .viewer-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .viewer-title {
          min-width: 0;
          display: grid;
          gap: 3px;
        }
        .viewer-title .title {
          font-size: 16px;
        }
        .viewer-details {
          display: grid;
          gap: 4px;
          padding: 0 2px;
        }
        .viewer-frame {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: #000;
          overflow: hidden;
        }
        video {
          width: 100%;
          aspect-ratio: 16 / 9;
          background: #000;
          display: block;
        }
        .no-video {
          width: 100%;
          aspect-ratio: 16 / 9;
          display: grid;
          place-items: center;
          background: #000;
          color: #fff;
        }
        .empty, .error {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 18px;
          color: var(--secondary-text-color);
          background: var(--card-background-color);
        }
        .error { color: var(--error-color); }
        @media (max-width: 900px) {
          .page {
            padding: 12px;
          }
          .toolbar {
            grid-template-columns: 1fr;
          }
          .stats-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .stat-value {
            font-size: 19px;
          }
          .clips {
            grid-template-columns: 1fr;
          }
          .clip {
            grid-template-rows: auto auto;
            min-height: 0;
            height: auto;
            overflow: visible;
          }
          .meta {
            min-height: 54px;
            padding-bottom: 14px;
          }
          .viewer {
            gap: 14px;
          }
          .viewer-bar {
            align-items: flex-start;
          }
          .viewer-frame {
            overflow: visible;
          }
          .viewer-details {
            padding-bottom: 10px;
          }
          video, .no-video {
            min-height: min(58vw, 360px);
          }
        }
      </style>
      <div class="page">
        ${useViewerPage ? "" : `${this.renderStats(this.data?.stats)}<div class="toolbar">
          <label>
            ${this.escape(this.t("camera"))}
            <select id="camera" ${cameras.length === 0 ? "disabled" : ""}>
              ${cameras.map((item) => `<option value="${this.escape(this.cameraKey(item))}" ${this.cameraKey(item) === this.selectedCameraKey ? "selected" : ""}>${this.escape(item.name)}</option>`).join("")}
            </select>
          </label>
          <label>
            ${this.escape(this.t("date"))}
            <select id="date" ${!camera?.dates?.length ? "disabled" : ""}>
              ${(camera?.dates || []).map((date) => `<option value="${this.escape(date)}" ${date === this.selectedDate ? "selected" : ""}>${this.escape(date)}</option>`).join("")}
            </select>
          </label>
          <div class="status">${this.escape(this.statusText(camera, clipCount))}</div>
          <button id="refresh" type="button">${this.escape(this.loading ? this.t("loading") : this.t("refresh"))}</button>
        </div>`}
        ${this.error ? `<div class="error">${this.escape(this.error)}</div>` : ""}
        ${!this.error ? (useViewerPage ? this.renderViewer(viewerClip) : this.renderBody(clips)) : ""}
      </div>
    `;
    this.bindEvents();
    this.afterRender();
  }

  renderBody(clips) {
    if (this.loading && !this.data) {
      return `<div class="empty">${this.escape(this.t("loadingRecordings"))}</div>`;
    }
    if (!this.data?.cameras?.length) {
      return `<div class="empty">${this.escape(this.t("noCamerasFoundSentence"))}</div>`;
    }
    if (!clips.length) {
      return `<div class="empty">${this.escape(this.t("noRecordingsForDate"))}</div>`;
    }
    return `<div class="clips">${clips.map((clip) => this.renderClip(clip)).join("")}</div>`;
  }

  renderStats(stats) {
    if (!stats) return "";
    const ready = Number(stats.ready_clips) || 0;
    const pending = Math.max(0, Number(stats.pending_clips) || 0);
    const onlineCameras = Number(stats.online_cameras) || 0;
    const totalCameras = Number(stats.total_cameras) || 0;
    const storage = Number(stats.total_bytes) || 0;
    const latest = stats.latest_clip || null;
    return `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">${this.escape(this.t("readyToWatch"))}</div>
          <div class="stat-value">${this.escape(this.formatNumber(ready))}</div>
          <div class="stat-sub">${this.escape(this.readyDetail(pending))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${this.escape(this.t("newestRecording"))}</div>
          <div class="stat-value">${this.escape(this.latestRecordingValue(latest))}</div>
          <div class="stat-sub">${this.escape(this.latestRecordingDetail(latest))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${this.escape(this.t("camerasOnline"))}</div>
          <div class="stat-value">${this.escape(this.cameraCountValue(onlineCameras, totalCameras))}</div>
          <div class="stat-sub">${this.escape(this.cameraCountDetail(onlineCameras, totalCameras))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${this.escape(this.t("storageUsed"))}</div>
          <div class="stat-value">${this.escape(this.formatBytes(storage))}</div>
          <div class="stat-sub">${this.escape(this.syncText(stats))}</div>
        </div>
      </div>
    `;
  }

  renderViewer(clip) {
    const clipKey = this.playbackKey(clip);
    const playbackUrl = this.playbackUrls.get(clipKey) || "";
    const playbackType = this.playbackTypes.get(clipKey) || "";
    const playbackError = this.playbackErrors.get(clipKey) || "";
    const preparing = this.playbackLoadingKey === clipKey;
    const videoSourceAttrs = playbackType === "hls"
      ? `data-hls-url="${this.escape(playbackUrl)}" data-playback-key="${this.escape(clipKey)}"`
      : `src="${this.escape(playbackUrl)}"`;
    return `
        <div class="viewer">
        <div class="viewer-bar">
          <button id="back" type="button">${this.escape(this.t("back"))}</button>
          <div class="viewer-title"></div>
        </div>
        <div class="viewer-frame">
          ${playbackUrl ? `<video id="viewer-video" controls autoplay playsinline disablepictureinpicture disableremoteplayback controlsList="nodownload noplaybackrate noremoteplayback" preload="auto" ${videoSourceAttrs}></video>` : `<div class="no-video">${this.escape(playbackError || (preparing ? this.t("preparingRecording") : this.t("selectRecordingToPlay")))}</div>`}
        </div>
        <div class="viewer-details">
          <div class="title">${this.escape(this.cameraName(clip.entry_id, clip.serial))} - ${this.escape(this.formatClipTime(clip))}</div>
          <div class="sub">${this.escape(this.formatDuration(clip.duration))} - ${this.escape(playbackUrl ? this.t("ready") : preparing ? this.t("preparing") : clip.cached ? this.t("cached") : this.t("notCached"))}</div>
        </div>
      </div>
    `;
  }

  renderClip(clip) {
    return `
      <div class="clip" role="button" tabindex="0" data-entry-id="${this.escape(clip.entry_id)}" data-serial="${this.escape(clip.serial)}" data-start="${clip.start}" data-end="${clip.end}">
        <div class="thumb">
          ${clip.signed_thumbnail_url ? `<img src="${this.escape(clip.signed_thumbnail_url)}" loading="lazy" alt="">` : `<div class="missing-thumb">${this.escape(this.t("noThumbnail"))}</div>`}<span class="badge">${this.escape(this.formatDuration(clip.duration))}</span>
        </div>
        <div class="meta">
          <div class="title">${this.escape(this.formatClipTime(clip))}</div>
          <div class="sub">${this.escape(clip.cached ? this.t("cached") : this.t("notCached"))}</div>
        </div>
      </div>
    `;
  }

  bindEvents() {
    this.shadowRoot.getElementById("camera")?.addEventListener("change", async (event) => {
      this.selectedCameraKey = event.target.value;
      this.selectedDate = this.camera?.dates?.[0] || "";
      this.selectedClip = null;
      await this.signVisibleThumbnails();
      this.render();
    });
    this.shadowRoot.getElementById("date")?.addEventListener("change", async (event) => {
      this.selectedDate = event.target.value;
      this.selectedClip = null;
      await this.signVisibleThumbnails();
      this.render();
    });
    this.shadowRoot.getElementById("refresh")?.addEventListener("click", () => this.loadData());
    this.shadowRoot.getElementById("back")?.addEventListener("click", () => this.closeViewer());
    this.shadowRoot.querySelectorAll(".clip").forEach((button) => {
      const open = async (event) => {
        if (event?.target?.closest?.("video")) return;
        const entryId = button.dataset.entryId;
        const serial = button.dataset.serial;
        const start = Number(button.dataset.start);
        const end = Number(button.dataset.end);
        const clip = this.findClip(entryId, serial, start, end);
        if (clip) {
          this.logPanelEvent("clip_open", this.clipDebugPayload(clip));
          await this.openClip(clip);
        }
      };
      button.addEventListener("click", open);
      button.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        open(event);
      });
    });
  }

  afterRender() {
    const video = this.shadowRoot.getElementById("viewer-video");
    if (!video) return;
    this.bindVideoDiagnostics(video);
    this.attachVideoSource(video).then(() => video.play?.()).catch((err) => {
      if (this.selectedClip) {
        this.logPanelEvent("video_autoplay_error", this.clipDebugPayload(this.selectedClip, {
          message: err?.message || String(err),
        }));
      }
    });
  }

  statusText(camera, clipCount) {
    if (this.loading && !this.data) return "";
    if (!camera) return this.t("noCameraSelected");
    const online = camera.online ? this.t("online") : this.t("offline");
    const total = (camera.clips || []).filter((clip) => clip.date === this.selectedDate).length;
    return this.t("recordingsCountStatus", {
      shown: this.formatNumber(clipCount),
      total: this.formatNumber(total),
      state: online,
    });
  }

  async signVisibleThumbnails() {
    await Promise.all(
      this.clips.map((clip) => this.signClip(clip, { thumbnail: true }))
    );
  }

  async signClip(clip, options = {}) {
    const signThumbnail = options.thumbnail === true;
    if (signThumbnail && clip.thumbnail_url) {
      clip.signed_thumbnail_url = await this.signPath(clip.thumbnail_url);
    }
  }

  async openClip(clip) {
    this.selectedCameraKey = this.clipKey(clip);
    this.selectedDate = clip.date || this.selectedDate;
    this.selectedClip = clip;
    const params = new URLSearchParams();
    params.set("entry_id", clip.entry_id);
    params.set("serial", clip.serial);
    params.set("start", String(clip.start));
    params.set("end", String(clip.end));
    window.history.pushState({ xsenseRecordingViewer: true }, "", `${window.location.pathname}${window.location.search}#${params.toString()}`);
    this.render();
    await this.prepareClipPlayback(clip);
    this.render();
  }

  closeViewer() {
    this.selectedClip = null;
    if (window.history.state?.xsenseRecordingViewer) {
      window.history.back();
      return;
    }
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    this.render();
  }

  syncRouteFromHash() {
    const hash = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(hash);
    const entryId = params.get("entry_id");
    const serial = params.get("serial");
    const start = Number(params.get("start") || 0);
    const end = Number(params.get("end") || 0);
    if ((!entryId || !serial || !start) || !this.data) {
      if (!entryId && !serial && !start) {
        this.selectedClip = null;
      }
      return;
    }
    const clip = this.findClip(entryId, serial, start, end);
    if (!clip) {
      this.selectedClip = null;
      this.error = this.t("recordingIsNotReady");
      this.logPanelEvent("route_clip_missing", { entry_id: entryId, serial, start, end });
      return;
    }
    this.selectedClip = clip;
    this.selectedCameraKey = this.clipKey(clip);
    this.selectedDate = clip.date || this.selectedDate;
    this.logPanelEvent("route_clip_selected", this.clipDebugPayload(clip));
  }

  findClip(entryId, serial, start, end) {
    for (const camera of this.data?.cameras || []) {
      const clip = (camera.clips || []).find((item) => item.entry_id === entryId && item.serial === serial && item.start === start && (!end || item.end === end));
      if (clip) return clip;
    }
    return null;
  }

  playbackKey(clip) {
    return `${clip.entry_id}:${clip.serial}:${clip.start}:${clip.end}`;
  }

  async prepareClipPlayback(clip) {
    if (!clip?.playback_url) {
      this.logPanelEvent("playback_skipped_missing_url", this.clipDebugPayload(clip));
      return;
    }
    const key = this.playbackKey(clip);
    const playbackPath = clip.playback_url;
    if (this.playbackUrls.has(key)) {
      this.logPanelEvent("playback_skipped_already_ready", this.clipDebugPayload(clip));
      return;
    }
    if (this.playbackLoadingKey === key) {
      this.logPanelEvent("playback_skipped_already_loading", this.clipDebugPayload(clip));
      return;
    }
    const startedAt = performance.now();
    this.playbackLoadingKey = key;
    this.playbackErrors.delete(key);
    this.render();
    try {
      this.logPanelEvent("playback_prepare_start", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
      }));
      const signedPath = await this.signPath(playbackPath);
      this.logPanelEvent("playback_signed_path_ready", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
        elapsed_ms: Math.round(performance.now() - startedAt),
      }));
      this.logPanelEvent("playback_fetch_start", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
        elapsed_ms: Math.round(performance.now() - startedAt),
      }));
      const response = await fetch(signedPath, {
        credentials: "same-origin",
        cache: "no-store",
      });
      this.logPanelEvent("playback_fetch_response", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
        status: response.status,
        ok: response.ok,
        content_type: response.headers.get("content-type") || "",
        elapsed_ms: Math.round(performance.now() - startedAt),
      }));
      if (!response.ok) {
        throw new Error(this.t("recordingIsNotReadyStatus", { status: response.status }));
      }
      const contentType = response.headers.get("content-type") || "";
      if (this.isHlsResponse(contentType, response.url || signedPath)) {
        this.setPlaybackUrl(key, signedPath, "hls");
        this.logPanelEvent("playback_hls_ready", this.clipDebugPayload(clip, {
          playback_url: playbackPath,
          content_type: contentType,
          message: this.hlsSupportMessage(),
          elapsed_ms: Math.round(performance.now() - startedAt),
        }));
        return;
      }
      const blob = await response.blob();
      if (!blob.size) {
        throw new Error(this.t("recordingEmpty"));
      }
      this.setPlaybackUrl(key, URL.createObjectURL(blob), "blob");
      this.logPanelEvent("playback_blob_ready", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
        bytes: blob.size,
        blob_type: blob.type || "",
        elapsed_ms: Math.round(performance.now() - startedAt),
      }));
    } catch (err) {
      this.playbackErrors.set(key, err?.message || String(err));
      this.logPanelEvent("playback_error", this.clipDebugPayload(clip, {
        playback_url: playbackPath,
        message: err?.message || String(err),
        elapsed_ms: Math.round(performance.now() - startedAt),
      }));
    } finally {
      if (this.playbackLoadingKey === key) {
        this.playbackLoadingKey = "";
      }
    }
  }

  setPlaybackUrl(key, url, type) {
    const previousUrl = this.playbackUrls.get(key);
    const previousType = this.playbackTypes.get(key);
    if (previousType === "blob" && previousUrl && previousUrl !== url) {
      URL.revokeObjectURL(previousUrl);
    }
    if (previousType === "hls") {
      this.hlsInstances.get(key)?.destroy?.();
      this.hlsInstances.delete(key);
    }
    this.playbackUrls.set(key, url);
    this.playbackTypes.set(key, type);
  }

  clearPlaybackUrl(key) {
    const previousUrl = this.playbackUrls.get(key);
    const previousType = this.playbackTypes.get(key);
    if (previousType === "blob" && previousUrl) {
      URL.revokeObjectURL(previousUrl);
    }
    this.hlsInstances.get(key)?.destroy?.();
    this.hlsInstances.delete(key);
    this.playbackUrls.delete(key);
    this.playbackTypes.delete(key);
  }

  disposePlaybackResources() {
    for (const hls of this.hlsInstances.values()) {
      hls.destroy?.();
    }
    this.hlsInstances.clear();
    for (const [key, url] of this.playbackUrls.entries()) {
      if (this.playbackTypes.get(key) === "blob") {
        URL.revokeObjectURL(url);
      }
    }
    this.playbackUrls.clear();
    this.playbackTypes.clear();
  }

  isHlsResponse(contentType, url) {
    const text = `${contentType || ""} ${url || ""}`.toLowerCase();
    return text.includes("mpegurl") || text.includes(".m3u8") || text.includes(".m3u");
  }

  hlsSupportMessage() {
    const video = document.createElement("video");
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      return "native_hls";
    }
    if (window.Hls?.isSupported?.()) {
      return "hls_js";
    }
    return "hls_js_loader";
  }

  async attachVideoSource(video) {
    const hlsUrl = video.dataset.hlsUrl || "";
    if (!hlsUrl) return;
    const key = video.dataset.playbackKey || "";
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      this.logPanelEvent("playback_hls_native_attached", this.clipDebugPayload(this.selectedClip, {
        playback_url: hlsUrl,
      }));
      return;
    }
    const Hls = await this.loadHlsLibrary();
    if (!Hls?.isSupported?.()) {
      throw new Error(this.t("hlsPlaybackUnsupported"));
    }
    for (const [instanceKey, instance] of this.hlsInstances.entries()) {
      if (instanceKey !== key) {
        instance.destroy?.();
        this.hlsInstances.delete(instanceKey);
      }
    }
    this.hlsInstances.get(key)?.destroy?.();
    const hls = new Hls({
      enableWorker: false,
      lowLatencyMode: false,
    });
    hls.on(Hls.Events.ERROR, (_event, data) => {
      this.logPanelEvent("playback_hls_js_error", this.clipDebugPayload(this.selectedClip, {
        playback_url: hlsUrl,
        type: data?.type || "",
        details: data?.details || "",
        fatal: Boolean(data?.fatal),
      }));
      if (data?.fatal) {
        this.clearPlaybackUrl(key);
        this.playbackErrors.set(key, data?.details || this.t("hlsPlaybackFailed"));
        this.render();
      }
    });
    this.hlsInstances.set(key, hls);
    hls.attachMedia(video);
    hls.loadSource(hlsUrl);
    this.logPanelEvent("playback_hls_js_attached", this.clipDebugPayload(this.selectedClip, {
      playback_url: hlsUrl,
    }));
  }

  async loadHlsLibrary() {
    if (window.Hls) return window.Hls;
    if (!this.hlsLibraryPromise) {
      this.hlsLibraryPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = HLS_JS_URL;
        script.async = true;
        script.onload = () => resolve(window.Hls);
        script.onerror = () => reject(new Error(this.t("couldNotLoadHlsPlayer")));
        document.head.appendChild(script);
      });
    }
    return this.hlsLibraryPromise;
  }

  clipDebugPayload(clip, extra = {}) {
    return {
      entry_id: clip?.entry_id || "",
      serial: clip?.serial || "",
      start: clip?.start || 0,
      end: clip?.end || 0,
      cached: Boolean(clip?.cached),
      playback_url: clip?.playback_url || "",
      ...extra,
    };
  }

  logPanelEvent(event, payload = {}) {
    if (!this._hass?.callApi) return;
    this._hass.callApi("POST", "xsense/recordings/panel/debug", {
      event,
      ...payload,
    }).catch(() => undefined);
  }

  bindVideoDiagnostics(video) {
    const clip = this.selectedClip;
    if (!clip) return;
    const events = ["loadedmetadata", "canplay", "playing", "waiting", "stalled", "error"];
    for (const eventName of events) {
      video.addEventListener(eventName, () => {
        const mediaError = video.error;
        this.logPanelEvent(`video_${eventName}`, this.clipDebugPayload(clip, {
          duration: Number.isFinite(video.duration) ? Math.round(video.duration * 1000) : null,
          ready_state: video.readyState,
          network_state: video.networkState,
          error_code: mediaError?.code || null,
          message: mediaError?.message || "",
        }));
      }, { once: true });
    }
  }

  cameraKey(camera) {
    return `${camera.entry_id}:${camera.serial}`;
  }

  clipKey(clip) {
    return `${clip.entry_id}:${clip.serial}`;
  }

  cameraName(entryId, serial) {
    return (this.data?.cameras || []).find((camera) => camera.entry_id === entryId && camera.serial === serial)?.name || serial;
  }

  async signPath(path) {
    if (this.signedPaths.has(path)) {
      return this.signedPaths.get(path);
    }
    const result = await this._hass.connection.sendMessagePromise({
      type: "auth/sign_path",
      path,
      expires: 3600,
    });
    this.signedPaths.set(path, result.path);
    return result.path;
  }

  formatClipTime(clip) {
    return `${this.formatTime(clip.start)} - ${this.formatTime(clip.end)}`;
  }

  formatTime(epochSeconds) {
    const locale = this._hass?.locale || {};
    const options = { hour: "numeric", minute: "2-digit", second: "2-digit" };
    if (locale.time_format === "12") {
      options.hour12 = true;
    } else if (locale.time_format === "24") {
      options.hour12 = false;
    }
    return new Date(Number(epochSeconds) * 1000).toLocaleTimeString(locale.language || undefined, options);
  }

  formatDuration(seconds) {
    const total = Number(seconds) || 0;
    const minutes = Math.floor(total / 60);
    const rest = total % 60;
    if (!minutes) return `${rest}s`;
    return `${minutes}m ${String(rest).padStart(2, "0")}s`;
  }

  formatNumber(value) {
    return new Intl.NumberFormat(this._hass?.locale?.language || undefined).format(Number(value) || 0);
  }

  formatBytes(bytes) {
    const size = Number(bytes) || 0;
    if (size < 1024) return `${size} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let value = size / 1024;
    let unit = units[0];
    for (let index = 1; index < units.length && value >= 1024; index += 1) {
      value /= 1024;
      unit = units[index];
    }
    const digits = value >= 10 ? 1 : 2;
    return `${value.toFixed(digits)} ${unit}`;
  }

  readyDetail(pending) {
    if (pending > 0) return this.t("stillSyncing", { count: this.formatNumber(pending) });
    return this.t("allCaughtUp");
  }

  latestRecordingValue(latest) {
    if (!latest?.start) return this.t("noneYet");
    return this.formatTime(latest.start);
  }

  latestRecordingDetail(latest) {
    if (!latest?.start) return this.t("noRecordingsReady");
    return `${latest.camera_name || this.t("genericCamera")} - ${this.formatDuration(latest.duration)}`;
  }

  cameraCountValue(online, total) {
    if (!total) return "0";
    return `${this.formatNumber(online)}/${this.formatNumber(total)}`;
  }

  cameraCountDetail(online, total) {
    if (!total) return this.t("noCamerasFound");
    if (online === total) return this.t("allCamerasOnline");
    if (!online) return this.t("allCamerasOffline");
    return this.t("offlineCount", { count: this.formatNumber(total - online) });
  }

  syncText(stats) {
    if (stats?.cache_only) return this.t("backgroundSyncControlsVisibility");
    if ((Number(stats?.pending_clips) || 0) > 0) return this.t("lazyCacheOnPlayback");
    return this.t("recordingsReady");
  }

  language() {
    const locale = this._hass?.locale || {};
    const raw = this._hass?.language || locale.language || "en";
    const normalized = String(raw).toLowerCase().replace("_", "-");
    const aliased = LANGUAGE_ALIASES[normalized];
    if (aliased) return aliased;
    const exact = Object.keys(TRANSLATIONS).find((key) => key.toLowerCase() === normalized);
    if (exact) return exact;
    const base = normalized.split("-")[0];
    return LANGUAGE_ALIASES[base] || (TRANSLATIONS[base] ? base : "en");
  }

  t(key, params = {}) {
    const language = this.language();
    const dictionary = TRANSLATIONS[language] || TRANSLATIONS.en;
    const template = dictionary[key] || TRANSLATIONS.en[key] || key;
    return template.replace(/\{(\w+)\}/g, (_match, name) => params[name] ?? "");
  }

  escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
}

customElements.define("xsense-recordings-panel", XSenseRecordingsPanel);
