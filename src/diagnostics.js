// This page records browser capabilities without loading the exploit framework.
(function () {
  "use strict";
  var output = document.getElementById("report");
  var status = document.getElementById("status");

  function send() {
    var match = /PlayStation 5\/(\d+\.\d+)/.exec(navigator.userAgent);
    var report = {
      stage: "BASELINE",
      run_id: Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8),
      version: "[[VERSION_PLACEHOLDER]]",
      build_time: "[[BUILD_TIME_PLACEHOLDER]]",
      user_agent: navigator.userAgent,
      firmware_user_agent: match ? match[1] : null,
      secure_context: window.isSecureContext === true,
      apis: {
        BigInt: typeof BigInt, Worker: typeof Worker, fetch: typeof fetch,
        MessageChannel: typeof MessageChannel, WebAssembly: typeof WebAssembly,
        SharedArrayBuffer: typeof SharedArrayBuffer,
      },
    };
    var body = JSON.stringify(report, null, 2);
    output.textContent = body;
    status.className = "";
    status.textContent = "Enviando beacon…";

    function failed(detail) {
      status.className = "error";
      status.textContent = "Falha no beacon: " + detail;
    }
    try {
      var request = new XMLHttpRequest();
      request.open("POST", "/beacon/BASELINE", true);
      request.timeout = 8000;
      request.setRequestHeader("Content-Type", "application/json");
      request.onload = function () {
        if (request.status !== 204) return failed("HTTP " + request.status);
        status.className = "ok";
        status.textContent = "Beacon HTTP 204 — confira BASELINE no log do host. Run: " + report.run_id;
      };
      request.onerror = function () { failed("rede indisponível"); };
      request.ontimeout = function () { failed("tempo esgotado após 8 segundos"); };
      request.send(body);
    } catch (error) {
      failed(error.message || String(error));
    }
  }

  document.getElementById("retry").onclick = send;
  send();
})();
