class XSensePlaybackPanel extends HTMLElement {
  connectedCallback() {
    this.style.display = "block";
    this.style.height = "100%";
    this.render();
  }

  render() {
    const params = new URLSearchParams(window.location.search);
    const entryId = params.get("entry_id");
    const serial = params.get("serial");
    const startTime = params.get("start_time");
    const cameraEntityId = params.get("camera_entity_id");
    const endTime = params.get("end_time");
    const mode = params.get("mode") || "webrtc";

    if (!entryId || !serial || !startTime || (mode !== "recording" && !cameraEntityId)) {
      this.innerHTML = "<p>Missing X-Sense recording details.</p>";
      return;
    }

    if (mode === "recording") {
      this.renderRecordingPlayer(entryId, serial, startTime, endTime);
      return;
    }

    const playbackPath =
      `/xsense/playback/${encodeURIComponent(entryId)}` +
      `/${encodeURIComponent(serial)}/${encodeURIComponent(startTime)}` +
      `?camera_entity_id=${encodeURIComponent(cameraEntityId)}`;

    this.innerHTML = `
      <style>
        :host {
          background: #111;
          display: block;
          height: 100%;
          min-height: calc(100vh - var(--header-height, 56px));
        }
        iframe {
          border: 0;
          display: block;
          height: 100%;
          min-height: calc(100vh - var(--header-height, 56px));
          width: 100%;
        }
      </style>
      <iframe title="X-Sense recording" allow="autoplay; fullscreen" src="${playbackPath}"></iframe>
    `;
  }

  renderRecordingPlayer(entryId, serial, startTime, endTime) {
    let recordingPath =
      `/xsense/recording/${encodeURIComponent(entryId)}` +
      `/${encodeURIComponent(startTime)}` +
      `?serial=${encodeURIComponent(serial)}`;
    if (endTime) {
      recordingPath += `&end_time=${encodeURIComponent(endTime)}`;
    }

    this.innerHTML = `
      <style>
        :host {
          background: #111;
          color: #eee;
          display: grid;
          grid-template-rows: 1fr auto;
          height: 100%;
          min-height: calc(100vh - var(--header-height, 56px));
        }
        video {
          background: #000;
          display: block;
          height: 100%;
          min-height: calc(100vh - var(--header-height, 104px));
          object-fit: contain;
          width: 100%;
        }
        .status {
          background: #1f1f1f;
          box-sizing: border-box;
          font: 14px/1.4 sans-serif;
          min-height: 48px;
          padding: 12px 14px;
        }
      </style>
      <video id="xsense-recording-video" controls autoplay playsinline src="${recordingPath}"></video>
      <div class="status" id="xsense-recording-status">Preparing X-Sense recording...</div>
    `;

    const statusEl = this.querySelector("#xsense-recording-status");
    const videoEl = this.querySelector("#xsense-recording-video");
    videoEl.addEventListener("loadedmetadata", () => {
      statusEl.textContent = "X-Sense recording is ready.";
    });
    videoEl.addEventListener("error", () => {
      statusEl.textContent = "Unable to open the X-Sense recording.";
    });
  }
}

customElements.define("xsense-playback-panel", XSensePlaybackPanel);
