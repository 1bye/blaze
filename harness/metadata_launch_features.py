#!/usr/bin/env python3
"""Compare launch-only dependency features with Cargo, including unchanged --locked locks.

One JSON object or JSON file: metadata, cargo, rustc, work (absolute paths). Build the
blaze-metadata metadata example first. The fixture deliberately has no app devtools
feature: --features facade/devtools adds a registry package outside the lockfile graph.
"""
from dataclasses import dataclass, fields
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import own_metadata


@dataclass(frozen=True)
class Config:
    metadata: str
    cargo: str
    rustc: str
    work: str


def main(config: Config):
    work = Path(config.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    fixture = work / "fixture"
    if fixture.exists():
        raise SystemExit(f"refusing to replace existing fixture: {fixture}")
    shutil.copytree(Path(__file__).parent / "metadata/launch_features", fixture)

    def run(name, args):
        result = subprocess.run([str(a) for a in args], cwd=fixture,
                                capture_output=True, text=True, env=os.environ)
        (work / (name + ".stdout")).write_text(result.stdout)
        (work / (name + ".stderr")).write_text(result.stderr)
        if result.returncode:
            raise AssertionError(f"{name} failed ({result.returncode}): {result.stderr}")
        return result.stdout

    version = dict(line.split(": ", 1) for line in
                   run("rustc-version", [config.rustc, "-vV"]).splitlines() if ": " in line)
    cfg = work / "host.cfg"
    cfg.write_text(run("rustc-cfg", [config.rustc, "--print", "cfg"]))
    run("initial-lock", [config.cargo, "generate-lockfile"])
    lock = fixture / "Cargo.lock"
    original = lock.read_bytes()
    assert b'name = "hdrhistogram"' not in original
    common = ["--filter-platform", version["host"], "--cfg-file", cfg,
              "--rustc-version", version["release"]]
    results = []
    # Check both no-lock and an existing lock, plus repeated feature enable/disable.
    for locked in [False, True]:
        for enabled in [False, True, True, False]:
            label = f"{len(results)}-{'locked' if locked else 'fresh'}-{'on' if enabled else 'off'}"
            lock.write_bytes(original)
            if not locked:
                lock.unlink()
            flags = ["--features", "facade/devtools"] if enabled else []
            if locked:
                flags += ["--locked"]
            cargo = json.loads(run(label + "-cargo", [config.cargo, "build", "--unit-graph",
                                "-Zunstable-options", *flags]))
            assert lock.read_bytes() == original, "Cargo changed the broad lockfile graph"
            ours = json.loads(run(label + "-blaze", [config.metadata, "--build", *common, *flags]))
            difference = own_metadata.graph_difference(own_metadata.of_resolve(ours),
                                                      own_metadata.unit_graph(cargo))
            assert difference is None, difference
            assert lock.read_bytes() == original, "Blaze changed the lockfile graph"
            programs = json.loads(run(label + "-programs", [config.metadata, "--build", "--programs",
                                  "--bin", "launch-features", *common, *flags]))
            assert len(programs) == 1 and programs[0]["name"] == "launch-features", programs
            ids = [package["id"] for package in ours["packages"]]
            assert len(ids) == len(set(ids)), "duplicate manifests"
            assert any("hdrhistogram" in node["id"] for node in ours["resolve"]["nodes"]) == enabled
            output = run(label + "-run", [config.cargo, "run", "--quiet", *flags])
            assert output == ("7\n" if enabled else "0\n"), output
            results.append({"case": label, "packages": len(ours["resolve"]["nodes"]),
                            "output": output.strip(), "lock_unchanged": True})
    # A real lockfile change still fails under --locked, on both sides.
    manifest = fixture / "Cargo.toml"
    manifest.write_text(manifest.read_text() + '\nbyteorder = "=1.5.0"\n')
    lock.write_bytes(original)
    for name, args in [
        ("cargo", [config.cargo, "metadata", "--format-version", "1", "--locked"]),
        ("blaze", [config.metadata, "--build", *common, "--locked"]),
    ]:
        result = subprocess.run([str(a) for a in args], cwd=fixture,
                                capture_output=True, text=True, env=os.environ)
        (work / (name + "-stale-lock.stderr")).write_text(result.stderr)
        assert result.returncode != 0, f"{name} accepted a stale lock"
        assert "--locked" in result.stderr and "lock file" in result.stderr, result.stderr
        assert lock.read_bytes() == original
    results.append({"case": "stale-lock", "cargo_and_blaze_reject": True,
                    "lock_unchanged": True})
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"passed": len(results), "results": str(work / "results.json")}))


if __name__ == "__main__":
    value = sys.argv[1]
    data = json.loads(value if value.startswith("{") else Path(value).read_text())
    unknown = data.keys() - {field.name for field in fields(Config)}
    if unknown:
        raise SystemExit(f"unknown config fields: {sorted(unknown)}")
    main(Config(**data))
