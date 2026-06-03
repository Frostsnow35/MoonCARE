const { spawnSync } = require("node:child_process");
const { existsSync } = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const args = process.argv.slice(2);

const candidates = [
  [path.join(root, ".venv", "Scripts", "python.exe")],
  ["python"],
  ["py", "-3"],
  ["python3"],
];

let lastError = "";

for (const candidate of candidates) {
  const executable = candidate[0];
  if (executable.includes(path.sep) && !existsSync(executable)) {
    continue;
  }

  const version = spawnSync(executable, [...candidate.slice(1), "--version"], {
    cwd: root,
    encoding: "utf-8",
    shell: process.platform === "win32",
  });

  if (version.error || version.status !== 0) {
    lastError = version.error ? version.error.message : version.stderr || version.stdout;
    continue;
  }

  const result = spawnSync(executable, [...candidate.slice(1), ...args], {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  process.exit(result.status ?? 0);
}

console.error("Could not find Python 3.10+.");
if (lastError) {
  console.error(lastError.trim());
}
console.error("Install Python from https://www.python.org/downloads/ and retry.");
process.exit(1);
