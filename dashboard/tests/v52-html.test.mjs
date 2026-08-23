import assert from "node:assert/strict";
import test from "node:test";

async function render(path) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("v52", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the V52 real-data sealed report", async () => {
  const response = await render("/science-v52");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /第一次真实数据实验/);
  assert.match(html, /SEALED TEST FAILED/);
  assert.match(html, /2\.894/);
  assert.match(html, /未建立/);
  assert.match(html, /CALCE 2016/);
});
