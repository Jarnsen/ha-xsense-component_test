# Security Policy

## Reporting a vulnerability

Please do not report security vulnerabilities in a public issue. Use GitHub's
private vulnerability reporting form instead:

https://github.com/Jarnsen/ha-xsense-component_test/security/advisories/new

Include the affected version, reproduction steps, impact, and any relevant
logs or proof of concept. We will acknowledge the report, investigate it, and
coordinate a fix before public disclosure.

For non-security bugs and feature requests, open a regular GitHub issue.

## Minimum-version compatibility tests

Home Assistant 2025.3.0 requires exactly `aiohttp 3.11.13`. The Python 3.13
test job retains that dependency to exercise the supported minimum as shipped.
The tests run as the runner user in a separate network namespace with only
loopback enabled. This allows local test servers without exposing the old
dependency to traffic from outside that namespace.

X-Sense does not package or pin this version at runtime. Home Assistant manages
the installed `aiohttp` version; users should keep Home Assistant up to date
for security fixes.
