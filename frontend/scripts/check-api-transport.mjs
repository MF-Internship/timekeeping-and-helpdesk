import { readdirSync, readFileSync, statSync } from "node:fs";
import { relative, resolve } from "node:path";
import process from "node:process";

const root = resolve(process.argv[2] ?? ".");
const approvedSuffix = "src/shared/transport/authenticated-fetch.ts";
const findings = [];

for (const path of sourceFiles(root)) {
  const relativePath = relative(root, path).replaceAll("\\", "/");
  const source = readFileSync(path, "utf8");
  const approved = relativePath.endsWith(approvedSuffix);
  if (!approved && /\bfetch\s*\([^)]*["'`]\/api\/v1\//s.test(source)) {
    findings.push(relativePath);
  }
  if (/from\s+["'](?:axios|ky|got)["']/.test(source)) findings.push(relativePath);
}

for (const finding of [...new Set(findings)].sort()) {
  process.stderr.write(`TRANSPORT-BOUNDARY: ${finding}\n`);
}
process.exitCode = findings.length === 0 ? 0 : 1;

function sourceFiles(path) {
  if (statSync(path).isFile()) return [path];
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) return [];
    const child = resolve(path, entry.name);
    if (entry.isDirectory()) return sourceFiles(child);
    return /\.[cm]?[jt]sx?$/.test(entry.name) ? [child] : [];
  });
}
