## 🔧 v.1.2.5.1

A focused MQTT startup hotfix. This release removes a Home Assistant event-loop warning introduced by the MQTT setup work in 1.2.5.

### ✨ Highlights

- 🏠 Moved MQTT connection preparation through the Home Assistant executor.
- 🔐 Deferred TLS certificate loading so it no longer runs on the Home Assistant event loop.

### 🛠️ Fixed

- Fixed MQTT TLS setup during both initial connect and reconnect paths.

### 🔎 Validation

- ✅ Full test suite passed.
- ✅ Diff checks passed.
