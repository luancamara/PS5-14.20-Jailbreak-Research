# Native installer

The installer ELF serves the loader on `http://127.0.0.1:18180/`, opens the PS5
browser, and installs the homescreen shortcut (`WKRL00001`) after AppCache installation.
An existing ELF loader is required to run it.

Build from the repository root with `make installer` (or `bash tools/build_release.sh`). The build uses Docker,
the PS5 payload SDK, `libmicrohttpd`, and the shared helpers in
[`common`](common/README.md). The SDK recipe and all installer sources are in
this repository; no submodules are required.
Output: `webkit-remote-loader-installer_v*.elf`.

The installer listens only on `127.0.0.1`. Its `/install`, `/exit`, and
`/clear-webkit-data` routes require POST and an `X-WKRLI-Action` header equal
to the route name without the leading slash. The bundled frontend sends it;
cross-origin preflights do not allow these mutation requests. Clearing WebKit
data still deletes the foreground user's browser data. This native installer
is separate from the browser research procedure in
[TESTE_PS5.md](../docs/TESTE_PS5.md) and has not been validated on PS5 by this fork.

App identity and embedded asset paths are configured in
`include/installer_config.h`. Ports, versions, thread names, HTTP routing, and
frontend resources stay in this installer. The release script pins one build
version for the native ELF, cache, and PC host.

Installer sources and binaries use [GPLv3](LICENSE). The loader's license is in
the repository root.
