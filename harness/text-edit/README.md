# String edit regression

This crate uses a function-like proc macro without Rake. `harness/textedit.py`
compares its normal and panic output with the pinned Cargo compiler, then repeats
after equal-length and longer UTF-8 string edits. Const and byte-array lengths,
`Location::caller()` and panic line/column must all update. The compiler's normal
sandbox remains enabled and all outputs/toolchains live in the supplied work
area.

Run from the repository's Python workspace:

```sh
uv run --frozen python harness/textedit.py '{"blaze":"/path/to/blaze","work":"/short/empty/path","toolchain_root":"/isolated/pinned/toolchain"}'
```

`hir-ide::tests::incremental::string_text_macro_edit_keeps_inference` is the small
query-level reproduction: both string edits used to execute inference again;
with the inference projection they reuse it. The companion tests retain
invalidation for byte lengths, const-computed lengths and string const arguments.
