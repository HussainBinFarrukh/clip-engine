import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("shell page names the product", () => {
  const source = readFileSync(
    new URL("../app/page.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /Clip Engine/);
  assert.match(source, /T02 scaffold/);
});
