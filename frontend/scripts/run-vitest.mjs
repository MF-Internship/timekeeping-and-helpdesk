import { spawnSync } from "node:child_process";

const WEB_STORAGE_FLAG = "--no-experimental-webstorage";
const existingNodeOptions = process.env.NODE_OPTIONS?.trim();
const nodeOptions = existingNodeOptions
  ? `${existingNodeOptions} ${WEB_STORAGE_FLAG}`
  : WEB_STORAGE_FLAG;

const result = spawnSync(
  process.execPath,
  ["./node_modules/vitest/vitest.mjs", "run", ...process.argv.slice(2)],
  {
    env: { ...process.env, NODE_OPTIONS: nodeOptions },
    stdio: "inherit",
  },
);

if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
