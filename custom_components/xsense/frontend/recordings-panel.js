const HLS_JS_URL = "/xsense_recordings_static/vendor/hls.light.min.js";

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
            Camera
            <select id="camera" ${cameras.length === 0 ? "disabled" : ""}>
              ${cameras.map((item) => `<option value="${this.escape(this.cameraKey(item))}" ${this.cameraKey(item) === this.selectedCameraKey ? "selected" : ""}>${this.escape(item.name)}</option>`).join("")}
            </select>
          </label>
          <label>
            Date
            <select id="date" ${!camera?.dates?.length ? "disabled" : ""}>
              ${(camera?.dates || []).map((date) => `<option value="${this.escape(date)}" ${date === this.selectedDate ? "selected" : ""}>${this.escape(date)}</option>`).join("")}
            </select>
          </label>
          <div class="status">${this.escape(this.statusText(camera, clipCount))}</div>
          <button id="refresh" type="button">${this.loading ? "Loading" : "Refresh"}</button>
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
      return `<div class="empty">Loading recordings...</div>`;
    }
    if (!this.data?.cameras?.length) {
      return `<div class="empty">No cameras found.</div>`;
    }
    if (!clips.length) {
      return `<div class="empty">No recordings for this date.</div>`;
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
          <div class="stat-label">Ready To Watch</div>
          <div class="stat-value">${this.escape(this.formatNumber(ready))}</div>
          <div class="stat-sub">${this.escape(this.readyDetail(pending))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Newest Recording</div>
          <div class="stat-value">${this.escape(this.latestRecordingValue(latest))}</div>
          <div class="stat-sub">${this.escape(this.latestRecordingDetail(latest))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Cameras Online</div>
          <div class="stat-value">${this.escape(this.cameraCountValue(onlineCameras, totalCameras))}</div>
          <div class="stat-sub">${this.escape(this.cameraCountDetail(onlineCameras, totalCameras))}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Storage Used</div>
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
          <button id="back" type="button">Back</button>
          <div class="viewer-title"></div>
        </div>
        <div class="viewer-frame">
          ${playbackUrl ? `<video id="viewer-video" controls autoplay playsinline disablepictureinpicture disableremoteplayback controlsList="nodownload noplaybackrate noremoteplayback" preload="auto" ${videoSourceAttrs}></video>` : `<div class="no-video">${this.escape(playbackError || (preparing ? "Preparing recording..." : "Select a recording to play"))}</div>`}
        </div>
        <div class="viewer-details">
          <div class="title">${this.escape(this.cameraName(clip.entry_id, clip.serial))} - ${this.escape(this.formatClipTime(clip))}</div>
          <div class="sub">${this.escape(this.formatDuration(clip.duration))} - ${playbackUrl ? "Ready" : preparing ? "Preparing" : clip.cached ? "Cached" : "Not cached"}</div>
        </div>
      </div>
    `;
  }

  renderClip(clip) {
    return `
      <div class="clip" role="button" tabindex="0" data-entry-id="${this.escape(clip.entry_id)}" data-serial="${this.escape(clip.serial)}" data-start="${clip.start}" data-end="${clip.end}">
        <div class="thumb">
          ${clip.signed_thumbnail_url ? `<img src="${this.escape(clip.signed_thumbnail_url)}" loading="lazy" alt="">` : `<div class="missing-thumb">No thumbnail</div>`}<span class="badge">${this.escape(this.formatDuration(clip.duration))}</span>
        </div>
        <div class="meta">
          <div class="title">${this.escape(this.formatClipTime(clip))}</div>
          <div class="sub">${clip.cached ? "Cached" : "Not cached"}</div>
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
    if (!camera) return "No camera selected";
    const online = camera.online ? "online" : "offline";
    const total = (camera.clips || []).filter((clip) => clip.date === this.selectedDate).length;
    return `${clipCount} of ${total} recordings - ${online}`;
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
      this.error = "Recording is not ready yet.";
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
        throw new Error(`Recording is not ready (${response.status})`);
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
        throw new Error("Recording is empty");
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
      throw new Error("HLS playback is not supported by this browser");
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
        this.playbackErrors.set(key, data?.details || "HLS playback failed");
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
        script.onerror = () => reject(new Error("Could not load HLS player"));
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
    if (pending > 0) return `${this.formatNumber(pending)} still syncing`;
    return "All caught up";
  }

  latestRecordingValue(latest) {
    if (!latest?.start) return "None yet";
    return this.formatTime(latest.start);
  }

  latestRecordingDetail(latest) {
    if (!latest?.start) return "No recordings ready";
    return `${latest.camera_name || "Camera"} - ${this.formatDuration(latest.duration)}`;
  }

  cameraCountValue(online, total) {
    if (!total) return "0";
    return `${this.formatNumber(online)}/${this.formatNumber(total)}`;
  }

  cameraCountDetail(online, total) {
    if (!total) return "No cameras found";
    if (online === total) return "All cameras online";
    if (!online) return "All cameras offline";
    return `${this.formatNumber(total - online)} offline`;
  }

  syncText(stats) {
    if (stats?.cache_only) return "Background sync controls visibility";
    if ((Number(stats?.pending_clips) || 0) > 0) return "Lazy cache on playback";
    return "Recordings are ready";
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
