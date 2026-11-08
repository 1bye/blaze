# Native proc-macro cross-file span join

The derive receives the struct keyword from a macro definition in `src/definition.rs`
and its identifier from the invocation in `src/main.rs`. It checks that the tokens
come from different files before joining their spans.

Run from this directory with pinned Cargo and with Blaze's rebuilt native server
installed beside the engine. Use separate target directories and a fresh Blaze store
when testing a server change.

```sh
CARGO_TARGET_DIR=target/cargo cargo run --locked --offline
CARGO_TARGET_DIR=target/blaze BLAZE_PROC_MACRO_WASM=0 BLAZE_SANDBOX=on blaze run --locked --offline
```

Both runs should print `cross-file join: None`.
