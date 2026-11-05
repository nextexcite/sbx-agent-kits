# Amp software-factory sandbox

- You are in an isolated sandbox with a non-root agent user.
- Installed toolchains: mise, uv, fnm (Node LTS), pnpm, Pi, Bun, Deno,
  agent-browser + Chromium, the skills CLI and GitHub CLI.
- Prefer project-local manifests (mise.toml, .node-version, pyproject.toml).
- Do not print credentials, access tokens, login profiles or secret contents.
- Work in a branch, test changes, and report changed files and validations.
- This sandbox may be short-lived. Push code and export durable artifacts.
- Network access is intentionally scoped to common package and Git hosts.
  Obtain explicit policy approval for other hosts; do not silently bypass it.
