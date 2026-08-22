import assert from "node:assert/strict";
import test from "node:test";

async function render(path) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("v51", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the V51 ten-gate capability report", async () => {
  const response = await render("/science-v51");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /把“10分”变成十道不能跳过的证据门/);
  assert.match(html, /9(?:<!-- -->)?\/10/);
  assert.match(html, /3(?:<!-- -->)?\/10/);
  assert.match(html, /REP51-d406a116a0d18618/);
  assert.match(html, /突破性发现/);
  assert.match(html, /未建立/);
});
