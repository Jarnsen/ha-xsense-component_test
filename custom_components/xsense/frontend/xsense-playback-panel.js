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

    if (!entryId || !serial || !startTime || !cameraEntityId) {
      this.innerHTML = "<p>Missing X-Sense recording details.</p>";
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
}

customElements.define("xsense-playback-panel", XSensePlaybackPanel);
