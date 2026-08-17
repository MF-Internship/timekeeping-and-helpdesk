import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { format } from "prettier";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const contract = resolve(frontendRoot, "../contracts/openapi.yaml");
const artifact = resolve(frontendRoot, "src/shared/api/schema.ts");
const mode = process.argv[2];

if (mode !== "--write" && mode !== "--check") {
  process.stderr.write("API-GENERATION: expected --write or --check\n");
  process.exit(2);
}

const executable = resolve(frontendRoot, "node_modules/.bin/openapi-typescript");
const generated = spawnSync(executable, [contract], {
  cwd: frontendRoot,
  encoding: "utf8",
  env: { ...process.env, NO_COLOR: "1" },
});

if (generated.status !== 0) {
  process.stderr.write("API-GENERATION: contracts/openapi.yaml\n");
  process.exit(1);
}

const candidate = await format(generated.stdout.replaceAll("\r\n", "\n"), {
  parser: "typescript",
  printWidth: 100,
  semi: true,
  singleQuote: false,
  trailingComma: "all",
});
if (mode === "--write") {
  writeFileSync(artifact, candidate, "utf8");
  process.exit(0);
}

let committed = "";
try {
  committed = readFileSync(artifact, "utf8");
} catch {
  // A missing generated artifact is drift.
}
if (committed !== candidate) {
  process.stderr.write("API-DRIFT: frontend/src/shared/api/schema.ts\n");
  process.exit(1);
}
