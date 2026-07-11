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

## Entity Changes

Entity changes that can affect dashboards or automations are tracked in [X-Sense Entity Changes](ENTITY_CHANGES.md).
