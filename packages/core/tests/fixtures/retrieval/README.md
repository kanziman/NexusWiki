# Representative retrieval fixture

This is a repository-owned, fictional corpus for repeatable retrieval evaluation. It never contains a tenant UUID, customer material, or production export. The corpus represents common support, operations, security, billing, Korean normalization, and graph-navigation scenarios.

`representative_corpus.v1.json` is the only corpus a local benchmark may seed. A run must generate a disposable local workspace marker and clean up only data carrying that marker. The fixture deliberately includes NFC/NFD and full-width query variants, dense/lexical cases, and resolved graph cycles so those paths are measurable without production data.

Hashes are SHA-256 of canonical JSON with the document's own `sha256` field omitted. Update the version and both pinned hashes whenever fixture content changes.
