/* Developer playground — talks to /api/v1 exactly the way a customer does.
 *
 * The single design decision worth explaining: this page calls the public API
 * from the browser with a key the developer pastes in, rather than proxying
 * through a portal endpoint that borrows their session.
 *
 * A proxy would have to reconstruct the caller's identity server-side and would
 * become a second way to reach the chargeable path — the one thing the platform
 * rules forbid, and the one place a policy bug costs real money. Pasting a key
 * means the playground *is* the API: same auth, same scopes, same rate limits,
 * same credit ledger, same idempotency. If it works here it works from a
 * server, and if it is refused here it would have been refused there.
 *
 * The key lives in a variable for the lifetime of the tab. It is never written
 * to localStorage, never sent anywhere except the Authorization header of
 * requests to this same origin, and the field is cleared on submit-to-nowhere.
 */
(function () {
  "use strict";

  var root = document.getElementById("playground");
  if (!root) return;

  var catalog = JSON.parse(document.getElementById("pg-catalog").textContent);
  var state = { tool: null, uploads: {} };

  var els = {
    tool: document.getElementById("pg-tool"),
    key: document.getElementById("pg-key"),
    form: document.getElementById("pg-form"),
    raw: document.getElementById("pg-raw"),
    rawWrap: document.getElementById("pg-raw-wrap"),
    rawToggle: document.getElementById("pg-raw-toggle"),
    quote: document.getElementById("pg-quote"),
    run: document.getElementById("pg-run"),
    out: document.getElementById("pg-out"),
    cost: document.getElementById("pg-cost"),
  };

  function show(message, kind) {
    els.out.textContent = message;
    els.out.className = "pg-out " + (kind || "");
  }

  function append(message) {
    els.out.textContent += "\n" + message;
  }

  function toolByName(name) {
    for (var i = 0; i < catalog.length; i += 1) {
      if (catalog[i].name === name) return catalog[i];
    }
    return null;
  }

  /* Build the form from the published JSON Schema — the same document the
     server validates against, so the form cannot offer a field the API
     rejects or miss one it requires. */
  function renderForm(tool) {
    els.form.innerHTML = "";
    state.uploads = {};
    var required = tool.input_schema.required || [];
    var props = tool.input_schema.properties || {};
    Object.keys(props).forEach(function (name) {
      var spec = props[name];
      var row = document.createElement("p");
      var label = document.createElement("label");
      label.setAttribute("for", "pg-f-" + name);
      label.textContent = name + (required.indexOf(name) >= 0 ? " *" : "");
      row.appendChild(label);
      row.appendChild(document.createElement("br"));

      var field;
      if (spec.enum) {
        field = document.createElement("select");
        if (required.indexOf(name) < 0) {
          field.appendChild(new Option("—", ""));
        }
        spec.enum.forEach(function (value) {
          field.appendChild(new Option(String(value), String(value)));
        });
      } else if (isMedia(spec)) {
        field = document.createElement("input");
        field.type = "file";
        field.dataset.media = "1";
      } else {
        field = document.createElement("input");
        field.type = spec.type === "integer" ? "number" : "text";
        if (spec.minimum !== undefined) field.min = spec.minimum;
        if (spec.maximum !== undefined) field.max = spec.maximum;
        if (spec.maxLength !== undefined) field.maxLength = spec.maxLength;
      }
      field.id = "pg-f-" + name;
      field.name = name;
      if (spec.default !== undefined && field.tagName !== "SELECT") {
        field.value = spec.default;
      } else if (spec.default !== undefined) {
        field.value = String(spec.default);
      } else if (spec.examples && spec.examples.length && !isMedia(spec)) {
        field.value = String(spec.examples[0]);
      }
      row.appendChild(field);

      if (spec.description) {
        var hint = document.createElement("small");
        hint.className = "muted";
        hint.textContent = " " + spec.description;
        row.appendChild(hint);
      }
      els.form.appendChild(row);
    });
    syncRaw();
  }

  function isMedia(spec) {
    return spec.type === "string" &&
      /Upload or artifact id|upload/i.test(spec.description || "");
  }

  function collect() {
    var payload = {};
    var props = (state.tool.input_schema.properties) || {};
    Object.keys(props).forEach(function (name) {
      var field = document.getElementById("pg-f-" + name);
      if (!field) return;
      if (field.dataset && field.dataset.media) {
        if (state.uploads[name]) payload[name] = state.uploads[name];
        return;
      }
      var value = field.value;
      if (value === "" || value === null) return;
      payload[name] = props[name].type === "integer" ? Number(value) : value;
    });
    return payload;
  }

  function syncRaw() {
    if (els.rawWrap.hidden) return;
    els.raw.value = JSON.stringify(collect(), null, 2);
  }

  function currentInput() {
    if (!els.rawWrap.hidden && els.raw.value.trim()) {
      return JSON.parse(els.raw.value);
    }
    return collect();
  }

  function headers(extra) {
    var base = {
      "Authorization": "Bearer " + els.key.value.trim(),
      "Content-Type": "application/json",
    };
    Object.keys(extra || {}).forEach(function (k) { base[k] = extra[k]; });
    return base;
  }

  function traceOf(response) {
    /* Only headers a caller is meant to act on. Nothing else is echoed. */
    var safe = ["X-Correlation-ID", "X-LTT-API-Version", "Retry-After",
                "Idempotency-Replayed", "Location"];
    var seen = [];
    safe.forEach(function (name) {
      var value = response.headers.get(name);
      if (value) seen.push(name + ": " + value);
    });
    return seen.join("\n");
  }

  function call(method, path, body, extra) {
    return fetch("/api/v1" + path, {
      method: method,
      headers: headers(extra),
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      return response.json().catch(function () { return {}; })
        .then(function (data) {
          return { ok: response.ok, status: response.status, data: data,
                   trace: traceOf(response) };
        });
    });
  }

  function requireKey() {
    if (!els.key.value.trim()) {
      show(root.dataset.needKey, "err");
      return false;
    }
    return true;
  }

  /* Media inputs go through the real upload flow: ticket, bytes, confirm. */
  function uploadPending() {
    var fields = els.form.querySelectorAll("input[data-media]");
    var chain = Promise.resolve();
    Array.prototype.forEach.call(fields, function (field) {
      if (!field.files || !field.files[0] || state.uploads[field.name]) return;
      var file = field.files[0];
      chain = chain.then(function () {
        return call("POST", "/uploads", {
          tool: state.tool.name, field: field.name,
          filename: file.name, content_type: file.type || "application/octet-stream",
          size: file.size,
        }).then(function (result) {
          if (!result.ok) throw new Error(JSON.stringify(result.data));
          var id = result.data.id;
          return fetch("/api/v1/uploads/" + id + "/content", {
            method: "POST",
            headers: { "Authorization": "Bearer " + els.key.value.trim(),
                       "Content-Type": file.type || "application/octet-stream" },
            body: file,
          }).then(function () {
            return call("POST", "/uploads/" + id + "/confirm", {});
          }).then(function (confirmed) {
            if (!confirmed.ok) throw new Error(JSON.stringify(confirmed.data));
            state.uploads[field.name] = id;
            append("upload " + field.name + " → " + id);
          });
        });
      });
    });
    return chain;
  }

  function doQuote() {
    if (!requireKey()) return Promise.resolve(null);
    show(root.dataset.working);
    return uploadPending().then(function () {
      return call("POST", "/quotes",
                  { tool: state.tool.name, input: currentInput() });
    }).then(function (result) {
      show(JSON.stringify(result.data, null, 2), result.ok ? "" : "err");
      if (result.trace) append("\n" + result.trace);
      els.cost.textContent = result.ok
        ? root.dataset.costs.replace("{n}", result.data.credit)
        : "";
      return result.ok ? result.data : null;
    }).catch(function (error) {
      show(String(error), "err");
      return null;
    });
  }

  function poll(id, tries) {
    return call("GET", "/jobs/" + id).then(function (result) {
      var status = result.data.status;
      append("… " + status);
      if (status === "queued" || status === "running") {
        if (tries <= 0) return result;
        return new Promise(function (resolve) {
          setTimeout(function () { resolve(poll(id, tries - 1)); }, 2000);
        });
      }
      return result;
    });
  }

  function doRun() {
    if (!requireKey()) return;
    doQuote().then(function (quote) {
      if (!quote) return;
      /* One key per logical call, generated here so a developer cannot forget
         it — and reused if they press Run twice with the same input, which is
         precisely the double-charge this header exists to prevent. */
      var key = state.idempotencyKey || (state.idempotencyKey = uuid());
      append("\nIdempotency-Key: " + key);
      return call("POST", "/jobs",
                  { tool: state.tool.name, quote: quote.quote,
                    input: currentInput() },
                  { "Idempotency-Key": key }).then(function (result) {
        append("\n" + JSON.stringify(result.data, null, 2));
        if (result.trace) append("\n" + result.trace);
        if (!result.ok) return;
        return poll(result.data.id, 30).then(function (final) {
          append("\n" + JSON.stringify(final.data, null, 2));
          var outputs = (final.data || {}).outputs || [];
          outputs.forEach(function (artifact) {
            append("artifact " + artifact.id);
          });
        });
      });
    });
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    return "pg-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  els.tool.addEventListener("change", function () {
    state.tool = toolByName(els.tool.value);
    state.idempotencyKey = null;
    els.cost.textContent = "";
    if (state.tool) renderForm(state.tool);
  });
  els.form.addEventListener("input", function () {
    /* Any change is a different call, so the previous key must not be reused:
       reusing it would replay the first answer instead of running the new
       input, and the API would be right to refuse. */
    state.idempotencyKey = null;
    syncRaw();
  });
  els.rawToggle.addEventListener("click", function () {
    els.rawWrap.hidden = !els.rawWrap.hidden;
    syncRaw();
  });
  els.quote.addEventListener("click", doQuote);
  els.run.addEventListener("click", doRun);

  state.tool = toolByName(els.tool.value);
  if (state.tool) renderForm(state.tool);
})();
