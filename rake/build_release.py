#!/usr/bin/env python3
"""Build the Apple Silicon Rake archive. One JSON object; no publication occurs."""
from dataclasses import dataclass, fields
from pathlib import Path
import gzip, hashlib, json, os, platform, shutil, subprocess, sys, tarfile, tempfile, urllib.request
ROOT = Path(__file__).resolve().parents[1]
@dataclass(frozen=True)
class Build:
    version: str
    out: str
    target_dir: str
    toolchain_root: str
    server_source: str = ""
    rustc_dev: str = ""
    jobs: int = 3

def run(args, **kw):
    subprocess.run([str(a) for a in args], check=True, **kw)
def digest(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def main(b):
    if (platform.system(),platform.machine()) != ("Darwin","arm64"):
        raise SystemExit("Rake Blaze releases require an Apple Silicon Mac")
    import re
    if not re.fullmatch(r"0\.\d{8}\.\d+-rake\.\d+",b.version): raise SystemExit("expected 0.YYYYMMDD.N-rake.N")
    pins=json.loads((ROOT/"rake/toolchain-server.json").read_text())
    current=(ROOT/"harness/toolchain").read_text().strip()
    tc=Path(b.toolchain_root).resolve(); target=Path(b.target_dir).resolve(); out=Path(b.out).resolve();out.mkdir(parents=True,exist_ok=True)
    declared=(ROOT/"crates/blaze-cargo/src/cargo/toolchain/pins.txt").read_text()
    if current!=pins["toolchain"] or "commit "+pins["rust_commit"] not in declared:
        raise SystemExit("macro-server source pin must be updated with harness/toolchain and pins.txt")
    vv=subprocess.check_output([tc/"bin/rustc","-vV"],text=True)
    if "commit-hash: "+pins["rust_commit"] not in vv: raise SystemExit("compiler and macro-server source revisions differ")
    env=dict(os.environ,PATH=str(tc/"bin")+os.pathsep+os.environ["PATH"],RUSTC=str(tc/"bin/rustc"),RUSTDOC=str(tc/"bin/rustdoc"),CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS=str(b.jobs),RUST_MIN_STACK="67108864",BLAZE_RELEASE="v"+b.version)
    for key in ["RUSTC_WRAPPER","RUSTC_WORKSPACE_WRAPPER","RUSTUP_TOOLCHAIN"]:env.pop(key,None)
    run([tc/"bin/cargo","build","--release","--locked","-p","blaze-engine","--bins"],cwd=ROOT,env=env)
    scratch=out/"server-source"
    if b.server_source:
        source=Path(b.server_source).resolve()
    else:
        archive=out/"rust-source.tar.gz"
        if not archive.exists():
            with urllib.request.urlopen("https://codeload.github.com/rust-lang/rust/tar.gz/"+pins["rust_commit"]) as response,archive.open("wb") as f:shutil.copyfileobj(response,f)
        if digest(archive)!=pins["source_sha256"]:raise SystemExit("Rust source checksum mismatch")
        scratch.mkdir(exist_ok=True)
        with tarfile.open(archive) as tar:tar.extractall(scratch,filter="data")
        source=scratch/("rust-"+pins["rust_commit"])/"src/tools/rust-analyzer"
    # Do not change a caller's source tree, including the earlier lab.
    local=out/"native-server-source"
    if local.exists():shutil.rmtree(local)
    shutil.copytree(source,local)
    f=local/"crates/proc-macro-srv-cli/src/main_loop.rs";s=f.read_text()
    old="assert_eq!(first.anchor.file_id, second.anchor.file_id);"
    new="if first.anchor.file_id != second.anchor.file_id {\n            return None;\n        }"
    if old in s:s=s.replace(old,new)
    elif new not in s:raise SystemExit("span_join source changed; review the patch before building")
    f.write_text(s)
    server_env=dict(env,CARGO_TARGET_DIR=str(target/"native-server"),RUSTFLAGS="-Lnative="+str(tc/"lib")+" -Crpath=yes")
    if b.rustc_dev:server_env["RUSTFLAGS"]="-Lall="+str(Path(b.rustc_dev).resolve())+" -Lnative="+str(tc/"lib")+" -Crpath=yes"
    run([tc/"bin/cargo","build","--release","--locked","-p","proc-macro-srv-cli","--features","in-rust-tree"],cwd=local,env=server_env)
    name="blaze-v"+b.version+"-aarch64-apple-darwin";stage=out/name
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir()
    for name_ in ["blaze","blaze-engine","blaze-rustc"]:shutil.copy2(target/"release"/name_,stage/name_)
    server=stage/"rust-analyzer-proc-macro-srv";shutil.copy2(target/"native-server/release/rust-analyzer-proc-macro-srv",server)
    libs=stage/"server-lib";libs.mkdir()
    # The native server links rustc_driver and LLVM. Bundle the matching libraries with
    # loader-relative rpaths rather than retaining paths into the build machine's sysroot.
    for name_ in ["libLLVM.dylib",*sorted(x.name for x in (tc/"lib").glob("librustc_driver-*.dylib"))]:shutil.copy2(tc/"lib"/name_,libs/name_)
    for binary in [server,*libs.iterdir()]:
        search="@loader_path/server-lib" if binary==server else "@loader_path"
        load_commands=subprocess.check_output(["otool","-l",binary],text=True)
        for old in re.findall(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path ([^\n]+) \(offset",load_commands):
            run(["install_name_tool","-delete_rpath",old,binary])
        run(["install_name_tool","-add_rpath",search,binary])
        run(["codesign","--force","--sign","-",binary])
    shared=stage/"share/blaze";shared.mkdir(parents=True)
    shutil.copytree(ROOT/"library",shared/"library")
    for name_ in ["LICENSE-APACHE","LICENSE-MIT","README.md","CHANGELOG.md","RAKE_FORK.md","RAKE_PATCHES.md"]:shutil.copy2(ROOT/name_,stage/name_)
    run([stage/"blaze","--version"])
    run([server,"--version"],env=dict(os.environ,RUST_ANALYZER_INTERNALS_DO_NOT_USE="1"))
    manifest={"version":b.version,"target":"aarch64-apple-darwin","base":"2007d7c8c849fd5a7858d5816e08764d9042c87c","commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"toolchain":current,"rust_commit":pins["rust_commit"],"files":{str(p.relative_to(stage)):digest(p) for p in sorted(stage.rglob("*")) if p.is_file()}}
    (stage/"RAKE_BLAZE.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
    archive=out/(name+".tar.gz")
    with archive.open("wb") as raw,gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode="w") as tar:
        for path in [stage,*sorted(stage.rglob("*"))]:
            info=tar.gettarinfo(path,str(path.relative_to(out)));info.uid=info.gid=0;info.uname=info.gname="";info.mtime=0
            if info.isfile():
                with path.open("rb") as f:tar.addfile(info,f)
            else:tar.addfile(info)
    sha=digest(archive);(out/"SHA256SUMS").write_text(sha+"  "+archive.name+"\n");(out/(archive.name+".sha256")).write_text(sha+"  "+archive.name+"\n")
    print(json.dumps({"archive":str(archive),"sha256":sha}))
if __name__=="__main__":
    value=sys.argv[1] if len(sys.argv)==2 else ""
    if value and not value.startswith("{"):value=Path(value).read_text()
    data=json.loads(value)
    unknown=set(data)-{f.name for f in fields(Build)}
    if unknown:raise SystemExit("unknown fields: "+str(sorted(unknown)))
    main(Build(**data))
