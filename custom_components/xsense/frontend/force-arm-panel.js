class XSenseForceArmPanel extends HTMLElement {
  set hass(value) {
    this._hass = value;
    this.runAction();
  }

  connectedCallback() {
    this._connected = true;
    this.render("Confirming X-Sense force arm...");
    this.runAction();
  }

  async runAction() {
    if (!this._connected || !this._hass || this._started) return;

    const params = new URLSearchParams(window.location.hash.slice(1));
    const entityId = params.get("entity_id");
    const mode = params.get("mode");
    if (!entityId || !["Home", "Away"].includes(mode)) {
      this.render("This X-Sense force-arm link is invalid.", true);
      return;
    }

    this._started = true;
    try {
      await this._hass.callService("xsense", "force_arm", {
        entity_id: entityId,
        mode,
      });
      this.render(`X-Sense is force arming in ${mode} mode.`);
      window.setTimeout(() => {
        if (window.history.length > 1) window.history.back();
        else window.location.assign("/");
      }, 800);
    } catch (error) {
      const message = error?.message || "The X-Sense force-arm request failed.";
      this.render(message, true);
    }
  }

  render(message, failed = false) {
    this.innerHTML = `
      <style>
        :host { display: block; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color); }
        main { max-width: 560px; margin: 0 auto; padding: 48px 24px; text-align: center; }
        h1 { font-size: 24px; letter-spacing: 0; margin: 0 0 16px; }
        p { line-height: 1.5; margin: 0; color: ${failed ? "var(--error-color)" : "var(--secondary-text-color)"}; }
        button { margin-top: 24px; border: 0; padding: 12px 20px; background: var(--primary-color); color: var(--text-primary-color); cursor: pointer; }
      </style>
      <main>
        <h1>X-Sense Security</h1>
        <p></p>
        ${failed ? "<button type=\"button\">Back</button>" : ""}
      </main>`;
    this.querySelector("p").textContent = message;
    this.querySelector("button")?.addEventListener("click", () => window.history.back());
  }
}

customElements.define("xsense-force-arm-panel", XSenseForceArmPanel);
