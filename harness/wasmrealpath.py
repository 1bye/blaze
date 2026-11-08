#!/usr/bin/env python3
"""Compare package path probes and XML validation in Cargo and Blaze's Wasm macro sandbox."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

MACRO = r'''extern crate proc_macro;
use proc_macro::TokenStream;
use std::{fs, io::ErrorKind, path::{Path, PathBuf}};

#[proc_macro_attribute]
pub fn check_xml(_: TokenStream, mut item: TokenStream) -> TokenStream {
    let package = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let xml = package.join("xml");
    let schema = xml.join("value.xml");

    assert_eq!(package.canonicalize().expect("package root"), package);
    assert_eq!(xml.canonicalize().expect("XML directory"), xml);
    assert_eq!(schema.canonicalize().expect("XML file"), schema);
    assert_eq!(package.join("inside.xml").canonicalize().unwrap(), schema);
    assert_eq!(
        package.join("missing.xml").canonicalize().unwrap_err().kind(),
        ErrorKind::NotFound,
    );

    let mut entries = fs::read_dir(xml.canonicalize().unwrap()).unwrap();
    assert_eq!(entries.next().unwrap().unwrap().file_name(), "value.xml");
    assert!(entries.next().is_none());
    assert_eq!(fs::read_to_string(schema.canonicalize().unwrap()).unwrap(), "<value>7</value>\n");

    let through_parent = package.join("../outside.xml");
    let through_link = package.join("outside.xml");
    if package == Path::new("/blaze/package") {
        assert_eq!(fs::read_link("/blaze").unwrap_err().kind(), ErrorKind::InvalidInput);
        assert_eq!(fs::read_link(&schema).unwrap_err().kind(), ErrorKind::InvalidInput);
        assert_eq!(fs::read_link(package.join("missing.xml")).unwrap_err().kind(), ErrorKind::NotFound);
        assert!(through_parent.canonicalize().is_err(), "parent traversal escaped");
        assert!(package.join("..").canonicalize().is_err(), "parent directory escaped");
        assert!(through_link.canonicalize().is_err(), "symlink escaped");
        assert!(fs::read_to_string(&through_parent).is_err(), "parent traversal read outside");
        assert!(fs::read_to_string(&through_link).is_err(), "symlink read outside");
    } else {
        assert_eq!(through_parent.canonicalize().unwrap(), through_link.canonicalize().unwrap());
        assert_eq!(fs::read_to_string(&through_link).unwrap(), "outside\n");
    }
    item.extend("const XML_CHECKED: bool = true;".parse::<TokenStream>().unwrap());
    item
}
'''

MAIN = '''#[xml_check::check_xml]
fn value() -> u32 { 7 }

fn main() { assert!(XML_CHECKED); println!("{}", value()); }
'''


@dataclass(frozen=True)
class Request:
    work: str
    blaze: str
    cargo: str
    cache: str
    toolchains: str

    def __post_init__(self):
        if any(not Path(path).is_absolute() for path in vars(self).values()):
            raise ValueError("all request paths must be absolute")


def run(request):
    os.umask(0o077)
    work = Path(request.work)
    app = work / "app"
    for directory in ("src", "xml", "xml-check/src"):
        (app / directory).mkdir(parents=True, exist_ok=False)
    (app / "Cargo.toml").write_text(
        '[package]\nname="wasm-realpath"\nversion="0.1.0"\nedition="2024"\n'
        '[workspace]\n[dependencies]\nxml-check={path="xml-check"}\n'
    )
    (app / "xml-check/Cargo.toml").write_text(
        '[package]\nname="xml-check"\nversion="0.1.0"\nedition="2024"\n[lib]\nproc-macro=true\n'
    )
    (app / "src/main.rs").write_text(MAIN)
    (app / "xml-check/src/lib.rs").write_text(MACRO)
    (app / "xml/value.xml").write_text("<value>7</value>\n")
    (work / "outside.xml").write_text("outside\n")
    (app / "inside.xml").symlink_to("xml/value.xml")
    (app / "outside.xml").symlink_to("../outside.xml")

    identity = hashlib.sha256(str(work).encode()).hexdigest()[:12]
    home = Path("/tmp") / f"blaze-wasm-realpath-{identity}"
    home.mkdir(mode=0o700)
    (home / "toolchains").symlink_to(request.toolchains)
    rustc = Path(request.cargo).with_name("rustc")
    env = dict(os.environ, PATH=str(rustc.parent) + os.pathsep + os.environ["PATH"],
               RUSTC=str(rustc), RUSTDOC=str(rustc.with_name("rustdoc")),
               BLAZE_HOME=str(home), BLAZE_CACHE=request.cache, BLAZE_BACKEND="cranelift",
               BLAZE_SANDBOX="on", BLAZE_SPARE="0", BLAZE_TIER="off", CARGO_BUILD_JOBS="1")
    for name in ("BLAZE_PROC_MACRO_WASM", "BLAZE_PROC_MACRO_SERVER", "BLAZE_PROFILE", "LOCKSTEP_XML_PATH"):
        env.pop(name, None)
    subprocess.run([request.cargo, "generate-lockfile", "--offline"], cwd=app, env=env, check=True)
    try:
        for lane, compiler in (("cargo", request.cargo), ("blaze", request.blaze)):
            current = dict(env, CARGO_TARGET_DIR=str(work / ("target-" + lane)))
            result = subprocess.run([compiler, "run", "--locked", "--offline"], cwd=app,
                                    env=current, capture_output=True, text=True, timeout=1200)
            (work / (lane + ".stdout")).write_text(result.stdout)
            (work / (lane + ".stderr")).write_text(result.stderr)
            assert result.returncode == 0, f"{lane}: exit {result.returncode}\n{result.stderr}"
            assert result.stdout == "7\n", f"{lane}: unexpected XML fixture output {result.stdout!r}"
            print(f"{lane}: {result.stdout.strip()}, package paths and XML checks passed", flush=True)
    finally:
        subprocess.run([request.blaze, "stop"], cwd=app, env=env, capture_output=True, timeout=120)


if __name__ == "__main__":
    (argument,) = sys.argv[1:]
    value = sys.stdin.read() if argument == "-" else argument if argument.lstrip().startswith("{") else Path(argument).read_text()
    run(Request(**json.loads(value)))
