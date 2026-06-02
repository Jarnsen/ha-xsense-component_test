## 🧪 v.1.2.3

A focused hotfix for X-Sense Test and Fire Drill controls after reports that 1.2.2 still did not trigger devices correctly.

### ✨ Highlights

- 🔐 Fixed AWS IoT shadow update signing so the exact signed JSON body is also the body sent to X-Sense.
- 📡 Sent compact pre-serialized shadow update bodies instead of allowing the HTTP client to reserialize them.
- 🚦 Surfaced rejected shadow updates as API errors instead of treating a failed button press as successful.

### 🛠️ Fixed

- Fixed mismatches between SigV4 payload hashes and transmitted shadow update bodies.
- Fixed silent success behavior when X-Sense rejected a shadow update.

### 🔎 Validation

- ✅ Added regression coverage proving the signed body and sent body are identical.
- ✅ Added regression coverage for rejected shadow update responses.
- ✅ Ran API tests and Python compilation checks.
