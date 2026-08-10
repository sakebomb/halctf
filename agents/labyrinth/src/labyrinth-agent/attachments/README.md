# Bundled challenge attachments

The agent pod CANNOT fetch these at runtime (confirmed run 5e3e7aa6: MCP
resources=[], get_challenge files=[], target port is the raw pwn socket). The
human competitor downloads them from the challenge page; drop them HERE and they
get baked into the image so the solver reads the local copy.

Expected files (exact names matter — solvers look for these):
  achilles_heel          <- Puzzle 1 binary (ELF). From the Achilles' Heel page.
  gatekeeper_stage1.py   <- Puzzle 7 leaked Python client. From the Gatekeeper page.

After dropping a file in, rebuild: ./build.sh v7
