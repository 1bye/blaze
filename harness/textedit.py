#!/usr/bin/env python3
"""String-only edits keep values, const lengths and source locations equal to Cargo.

Input: {"blaze": "/path/to/blaze", "work": "/short/empty/directory",
        "toolchain_root": "/path/to/the/pinned/toolchain"}.
The miniature uses a function-like proc macro and no Rake. The incremental unit
regression additionally checks that equal-length and longer text skip inference.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

from typed_input import parse


@dataclass(frozen=True)
class Input:
    blaze: str
    work: str
    toolchain_root: str


def main(config):
    root = Path(__file__).resolve().parent
    work = Path(config.work).resolve()
    project = work / "project"
    shutil.copytree(root / "text-edit", project)
    blaze = Path(config.blaze).resolve()
    toolchain = Path(config.toolchain_root).resolve()
    toolchains = work / "home/toolchains"
    toolchains.mkdir(parents=True)
    (toolchains / toolchain.name).symlink_to(toolchain, target_is_directory=True)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("BLAZE_", "RAKE_"))}
    env.update(PATH=str(toolchain / "bin") + os.pathsep + env["PATH"],
               RUSTC=str(toolchain / "bin/rustc"), RUSTDOC=str(toolchain / "bin/rustdoc"),
               RUST_MIN_STACK="67108864", RUST_BACKTRACE="0", CARGO_BUILD_JOBS="3",
               BLAZE_HOME=str(work / "home"), BLAZE_CACHE=str(work / "store"),
               BLAZE_PROC_MACRO_WASM="0", BLAZE_PROC_MACRO_SERVER="0",
               BLAZE_TOOLCHAIN_PROC_MACRO_SERVER=str(blaze.parent / "rust-analyzer-proc-macro-srv"),
               BLAZE_SANDBOX="on", BLAZE_MEMORY_MAX="16G", BLAZE_TIER="off", BLAZE_SPARE="0",
               BLAZE_STD_FROM="off", BLAZE_STATS="1")
    source = project / "src/main.rs"
    original = source.read_text()
    variants = [original,
                original.replace("text-one", "text-two"),
                "\n\n" + original.replace("text-one", "longer UTF-8 text: café")
                .replace("const-one", "a longer constant").replace("bytes-one", "longer bytes")
                .replace("panic-one", "a longer panic prefix")
                .replace("title, tracked()", "title,     tracked()")
                .replace("    panic!", "        panic!")]
    rows = []
    try:
        for index, text in enumerate(variants):
            source.write_text(text)
            for mode in ([], ["panic"]):
                outputs = {}
                for compiler, command in [("cargo", toolchain / "bin/cargo"), ("blaze", blaze)]:
                    current = dict(env, CARGO_TARGET_DIR=str(work / compiler))
                    ran = subprocess.run([str(command), "run", "--quiet", "--locked", "--bin", "text-edit-probe", "--", *mode],
                                         cwd=project, env=current, text=True, capture_output=True, timeout=600)
                    (work / f"{index}-{compiler}-{'panic' if mode else 'normal'}.log").write_text(ran.stderr)
                    outputs[compiler] = ran.stdout
                    assert (ran.returncode != 0) == bool(mode), (compiler, index, mode, ran.returncode, ran.stderr[-4000:])
                assert outputs["cargo"] == outputs["blaze"], (index, mode, outputs)
                rows.append({"edit": index, "panic": bool(mode), "output": outputs["blaze"]})
                print(json.dumps(rows[-1]), flush=True)
    finally:
        subprocess.run([str(blaze), "stop"], cwd=project, env=env, capture_output=True, timeout=30)
    (work / "results.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main(parse(Input, sys.argv[1], "textedit.py"))
