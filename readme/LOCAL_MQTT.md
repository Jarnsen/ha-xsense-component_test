# SBS50 Local MQTT

The integration can provision the SBS50 native MQTT feature from its options
menu. This follows the X-Sense Android app's Home Assistant configuration path.

## Setup

1. Configure a reachable MQTT broker and Home Assistant's MQTT integration with
   discovery enabled. Create a dedicated broker account for the SBS50.
2. Open the X-Sense integration options and choose **Set up SBS50 broker**.
3. Select the base station and enter the broker's LAN IPv4 address, port,
   username, and password, then submit.
4. Wait for the station to confirm it saved the settings. Then check the
   connection status separately in the X-Sense app. Supported detectors should
   appear under Home Assistant's **MQTT** integration after the SBS50 publishes
   discovery messages. Saving the settings does not confirm that the base
   station connected or published data.
5. Under **Device transport**, select a supported detector and check **Use
   Local MQTT only**. Leave it unchecked to keep the existing cloud behavior.

The APK gates the feature at SBS50 firmware 1.7.0. The firmware implements the
actual publishing, so availability may vary by firmware and device model.
The APK lists SBS50-linked Link+ Pro smoke, CO, combination smoke/CO, and heat
alarms. This is not a local transport for cameras or every X-Sense product.

## Cloud and Device Identity

Initial provisioning requires a working X-Sense cloud session. Broker credentials
are sent through that existing authenticated channel to the base station. They
are not saved in this integration's config entry, logged, or prefilled later.

After provisioning, native MQTT messages travel from the base station to the
local broker. A detector set to **Use Local MQTT only** uses the verified local
state below on its existing X-Sense entities. It does not use cloud state or
cloud commands. Cloud-only controls and readings are unavailable for that
detector. Shared station reports may still contain its data; the integration
does not apply that data to the selected detector. Other devices, including
cameras, keep their existing cloud paths.

Local-only detectors load from saved identity information even if the X-Sense
cloud is down at Home Assistant startup. They accept retained state and go
unavailable if Home Assistant loses its broker connection. All three supported
models also use their verified detector Online/Offline topic for availability.
Neither a connected broker nor a retained state proves the station is still
publishing. This does not establish what works when the station has no internet.

Native MQTT discovery is owned by Home Assistant's MQTT integration. The existing
cloud entities remain intact, so enabling both can create separate devices and
entities. Existing entity IDs, history, and automations are not migrated.

With Home Assistant's MQTT integration loaded, the existing XS0B-MR and
XS01-M smoke and end-of-life entities also listen for live SBS50 reports on
the standard discovery prefix. Matching requires the exact station and child
serials. The packet formats are documented in the
[XS0B-MR capture](https://forum.iobroker.net/topic/81775/test-adapter-xsense-x-sense/190)
and the [XS01-M broker report](https://github.com/cschnidr/openhab-xsense-mqtt).
The existing XH02-M heat alarm entity also accepts live reports on the
[documented heat alarm topic](https://github.com/arteck/ioBroker.xsense/blob/b65e18dc830f3a4a5d461d5a9c7aaa6c31b1a224/test/haTopics.test.js).
For detectors not set to local-only, an active cloud indication takes
precedence over a local clear, and a broker disconnect drops the local
reading. Cloud-backed entities still ignore retained local state.

For alarm state (not end of life), a cloud clear can replace a missed local
clear only when the clear report carries a device timestamp newer than the
local alarm receipt. Untimestamped reports and unrelated telemetry do not
clear the local alarm.

Enable debug logging on the X-Sense integration to see local state changes
and cloud clear recovery decisions. For an unmapped model, a redacted device
diagnostics export from Home Assistant's MQTT integration can provide the
discovery and state payloads that X-Sense does not yet subscribe to. Keep the
same replacement identifiers across topics and payloads so they can be matched.
To return a detector to cloud behavior, uncheck **Use Local MQTT only**.
That does not disable the shared broker. Disable station publishing in the
X-Sense app if no devices use it. Home Assistant manages its native MQTT
discovery entities separately.

## Protocol Reference

APK 1420: `XsHomeAssistantActivity`, `XsHaBean`, and `Q2/a,b,c,d`.
The desired command uses `appHaParam` on `2nd_haparam`. Saved configuration and
link state are separate reported shadows: `2nd_haparamup` and `2nd_halinkup`.
The command uses station identity, the account user-ID code, string-valued broker
fields, `source=1`, and a UTC `yyyyMMddHHmmss` timestamp.

Automated tests verify this request contract and configuration UI. Physical
SBS50 publishing and broker reconnection have not been validated by these tests.
