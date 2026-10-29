// Run the real baseline page script with a simulated browser and beacon response.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../src/diagnostics.js", import.meta.url), "utf8");
for (const outcome of [204, 500, "error", "timeout"]) {
  const nodes = Object.fromEntries(["report", "status", "retry"].map(id => [id, {}]));
  let request;
  const context = vm.createContext({
    navigator: { userAgent: "Mozilla/5.0 (PlayStation; PlayStation 5/14.20)" },
    document: { getElementById: id => nodes[id] },
    XMLHttpRequest: function () {
      request = this;
      this.open = (method, path) => { assert.equal(method, "POST"); assert.equal(path, "/beacon/BASELINE"); };
      this.setRequestHeader = () => {};
      this.send = body => {
        const data = JSON.parse(body);
        assert.equal(data.firmware_user_agent, "14.20");
        assert.equal(data.stage, "BASELINE");
        assert(data.run_id);
      };
    },
  });
  context.window = context;
  vm.runInContext(source, context);
  assert.equal(request.timeout, 8000);
  if (typeof outcome === "number") {
    request.status = outcome;
    request.onload();
  } else {
    request["on" + outcome]();
  }
  assert.match(nodes.status.textContent, outcome === 204 ? /204/ : /Falha/);
  assert.equal(nodes.status.className, outcome === 204 ? "ok" : "error");
  assert.equal(typeof nodes.retry.onclick, "function");
  nodes.retry.onclick();
}
console.log("Baseline: report, POST beacon, HTTP failure, network failure, timeout and retry passed");
