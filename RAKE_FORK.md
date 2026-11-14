# Rake Blaze fork

Apple Silicon-only pinned hybrid distribution. The rake.1 and rake.2 prereleases
are published in `1bye/blaze`; rake.3 adds the launch-feature manifest fix.

## Verified upstream history

Base: `v0.20261030.1`, `6560553cc09f00d8d96edc24d85a5e441352ab7c` from indexable-inc/blaze. The fork has the same root history and can become a GitHub fork. The old recovered-root branch is preserved as `snapshot-archive` and is not an ancestor of this release branch.

The recovered root snapshot `2007d7c` differs from this base by 30 files, +862/-58 lines. A fresh upstream clone, all requested tags, and all reachable main ancestors dated October 26 through November 2 were compared. The next candidates are `5cf29cd` (31 files, +879/-58) and `v0.20261030.0` (32 files, +957/-75). `v0.20261028.0` differs in 5904 files. Both WASI realpath and span_join are lab changes, not upstream at the base.

## Patches

The seven requested engine fixes are separate commits: confined WASI realpath with existence-sensitive cache keys; cross-file span_join returns None; `blaze.std::` symbols and std cache bump; module_path substitution in symbol attributes; canonical CARGO; real rustc build-script probes in hybrid mode; AArch64 NEON intrinsics. A separate native-server build commit selects and bundles the matching fixed toolchain server. A separate release commit defines this distribution.

The snapshot also contained eight earlier lab fixes, preserved as explicit prerequisite commits rather than hidden inside a root snapshot: job limits and NUM_JOBS keys; per-macro Wasm graph roots; bounded synchronous Wasm preparation; Wasm inlining; MIR storage conflict deltas; linker-used data and verbatim symbols; C ABI projected-field normalization; x86 AES keygen assist. The job-limit commit includes a missing test fixture profile field. There is no other unexplained snapshot source drift. See RAKE_PATCHES.md and the clean commit list.

## Changes after the initial fork release

- rake.2: reuse inference after string text edits (`d72f0bcab`), retaining format,
  byte-string and caller-location correctness checks.
- rake.3: load manifests introduced only by requested dependency features
  (`94016f1d7`), using the matching resolver graph's checksums. This fixes the
  `no manifest of hdrhistogram v7.6.0 was read` failure under `rake dev --live --cdp`.
  Cargo.lock still uses Cargo's broad graph, with no app-level `devtools` forwarding
  feature required. `harness/metadata_launch_features.py` compares nine cases
  against pinned Cargo, including feature toggles and stale `--locked` rejection.

## Build and archive

`python3 rake/build_release.py <config.json>` uses the owner-approved pinned Cargo bootstrap, no PGO or LLVM tiers. JSON fields: version, out, target_dir, toolchain_root; optional server_source, rustc_dev, jobs. The toolchain and native server must match harness/toolchain and rake/toolchain-server.json. A stock rustup toolchain needs its rustc-dev component in an isolated RUSTUP_HOME. Server sources are copied or fetched with a pinned checksum; the original engine and toolchain are never changed.

The standard `blaze-v<V>-aarch64-apple-darwin/` archive contains the three compiler binaries, source library, fixed native server and matching loader-relative libraries. RAKE_BLAZE.json records the true upstream base, release commit and file hashes. Set BLAZE_TOOLCHAIN_PROC_MACRO_SERVER to the packaged server in hybrid mode. SHA256SUMS authenticates the exact archive; rebuilding may change its checksum.

## Upgrade

1. `git fetch upstream --tags`
2. `git rebase --onto <new-upstream-tag> "$(cat rake/upstream-base)" rake-patches`
3. Review each fix and update rake/upstream-base to the new tag's full commit. If harness/toolchain changes, update rake/toolchain-server.json and its Rust source checksum together. Do not silently drop inherited fixes.
4. Build locally, run the fork unit tests, WASI and span fixtures, NEON/JPEG differential probes, and `python3 rake/acceptance.py <config.json>`. Run Rake workspace, live-runtime, supervisor and installer tests. Measure six warm text/helper edits behind the editor and record the first post-cold edit separately.
5. Only after owner authorization: create the actual GitHub fork, push this branch, tag/cut an Apple Silicon release and update Rake's URL and checksum from those bytes. Only the two release workflows are active. No Indexable services, secrets or runners are used.

Expected upkeep: 2–4 hours for a compatible bump; one or more days when Cranelift, rust-analyzer or the proc-macro ABI changes. The eight additional inherited fixes increase review scope; their clean history makes each visible on rebase.

The upstream AGENTS.md describes upstream infrastructure and self-hosting policy. This owner-authorized local distribution uses the pinned Cargo bootstrap and does not invoke landing tools.
