ARXIV ANCILLARY FILES

The paper proves c_E > 0.38055925 for the Erdos minimum-overlap constant.

The anc directory contains the project-original center certificate,
the Python-Arb and MPFI/C center checkers, and machine-readable verification
records. The complete maintained repository and exact release archive are
identified in the paper.

Price's noncentral source and certificate are not included because the pinned
repository state had no declared license. The aggregate replay record gives
the original repository, commit, source paths, SHA-256 hashes, exact command,
coverage, and certified result. The project-generated CSV, JSON, and log from
all 170 retained noncentral checks are included under anc/evidence.

MANIFEST.sha256 authenticates every file in this source bundle.

PYTHON-ARB REPLAY

python3 -m venv .venv
.venv/bin/python -m pip install -r anc/python/requirements.txt
.venv/bin/python anc/python/verify_center.py \
  anc/certificates/center-038055925.tsv

The JSON output must report certified=true, certificate SHA-256
b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8,
and a positive denominator_margin.

MPFI/C REPLAY

python3 anc/c/build_center_mpfi.py
./center_mpfi anc/certificates/center-038055925.tsv 256 4096 16

The output must end with status=pass and a positive denominator_margin_lower.
