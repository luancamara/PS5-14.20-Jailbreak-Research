// The loader must preserve the console's reported firmware and reject unknown versions.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../src/firmware.js", import.meta.url), "utf8");
for (const [version, supported] of [["7.61", true], ["9.05", true], ["10.40", true],
  ["13.60", true], ["14.20", false], ["99.99", false]]) {
  const context = vm.createContext({
    navigator: { userAgent: `Mozilla/5.0 (PlayStation; PlayStation 5/${version})` }, window: {},
  });
  vm.runInContext(source, context);
  assert.equal(context.window.fw_str, version);
  assert.equal(context.window.firmware.rejection(),
    supported ? null : `FW ${version} is not supported`);
}
console.log("Firmware detection: reported versions preserved; unsupported versions rejected");
