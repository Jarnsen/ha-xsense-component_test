# Updating X-Sense

## Home Assistant 2026.7 and Older Builds

If you are still using an old `v1.2.6.x` build, update to `v1.3.14` or newer before upgrading Home Assistant Core to 2026.7 or newer.

The old `v1.2.6.x` builds required `aiortc`, which is not compatible with Home Assistant's Python 3.14 runtime. Current releases no longer require `aiortc`.

## HACS Update Information

This integration is installed as a HACS custom repository.

If Home Assistant does not show an update immediately:

1. Open HACS.
2. Select the X-Sense repository.
3. Use the three-dot menu to run **Update information**.
4. Update or redownload the integration.
5. Restart Home Assistant.

## Installing a Pre-release

Pre-release (beta) builds are published as GitHub pre-releases. HACS 2.0 removed
the old "Show beta versions" toggle from the download dialog. To receive a
pre-release you must enable the repository's pre-release **switch entity**:

1. In Home Assistant, go to **Settings → Devices & Services → Entities**.
2. Search for the X-Sense HACS **pre-release** switch. It is disabled by
   default, so enable the entity first, then wait ~30 seconds for it to appear.
3. Turn the switch **on** so HACS includes pre-releases in update checks.
4. Open HACS, select the X-Sense repository, and use the three-dot menu to run
   **Update information**.
5. **Redownload** (or Update) and select the pre-release version, then restart
   Home Assistant.

## Entity Changes

Entity changes that can affect dashboards or automations are tracked in [X-Sense Entity Changes](ENTITY_CHANGES.md).
