# Patch provenance

All release commits descend from upstream v0.20261030.1 (6560553cc09f00d8d96edc24d85a5e441352ab7c). The archived recovered root 2007d7c is reference evidence only. See RAKE_FORK.md for the seven engine fixes and eight explicitly preserved earlier lab fixes.

WASI realpath and cross-file span_join were already present in the recovered snapshot but are absent from the verified upstream base. They are real lab patches in the reconstructed history. The seven requested fixes, native-server packaging, and release recipe are independently reviewable commits. Original licenses are retained.

The rake.2 text-edit inference fix is `d72f0bcab`. The rake.3 launch-feature manifest
fix is `94016f1d7`: both resolver graphs supply their newly discovered manifests,
while Cargo.lock semantics remain unchanged. Its differential regression is
`harness/metadata_launch_features.py`. No sandbox or fallback policy changed.
