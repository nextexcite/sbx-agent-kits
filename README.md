# Docker Sandboxes agent kits

Reference source for an Amp development environment in two OCI formats:

- **v2:** a Kit descriptor referring to a separately built OCI runtime image.
- **v3:** a self-contained workload build context using the pinned Kit frontend.

The v2 descriptor is not a runnable container image. The runtime Dockerfile
and v3 workload image are ordinary OCI images, but Docker Sandboxes lifecycle,
network policy and credential injection require the corresponding runtime.

## Scope and safety

This reference includes templates, a shared toolchain installer, context staging
and offline structural tests. It includes no deployment, registry publishing,
account configuration, cloud resource management or credential workflows.
Neither the tests nor GitHub Actions create a sandbox or publish an image.
Agent permission bypass is not enabled by these examples.

The default base is `dhi.io/sbx-templates:shell-docker`. Access and compatibility
must be checked in a separately authorized private build environment. Public CI
does **not** authenticate to that registry or claim to build or run this image.
Do not put credentials in source, build arguments, image layers or build logs.

## Offline checks and staging

Requires Python 3 and Bash. No service credentials or container daemon needed:

    python3 -m unittest discover -s tests -v
    bash scripts/check.sh
    bash scripts/stage-v3.sh
    IMAGE_REFERENCE=example.invalid/agent/runtime:local bash scripts/render-v2.sh

The image reference above is deliberately nonresolving. Replace it privately
with your runtime image reference before using a v2 descriptor. Generated
contexts live in `dist/` and are not committed.

To build the v2 runtime on a separately authorized host, use the repository
root as the Docker build context and `kits/v2/Dockerfile` as the Dockerfile.
For v3, stage the context first, then use a compatible Kit v3 builder. These
are templates, not a promise of availability or a tested cloud deployment.

## Toolchains and limitations

The shared installer includes Amp, mise, uv, fnm-managed Node LTS, pnpm, Pi,
Bun, Deno, agent-browser, distribution Chromium, skills and GitHub CLI.
The runtime is the `agent` user with UID 1000. The templates target Linux
amd64/arm64, but offline CI cannot verify architecture-specific runtime support.

The Kit frontend is digest-pinned. The base image tag, upstream installers and
several packages float. Builds are not reproducible or supply-chain verified;
review and pin these dependencies before production use. The installer runs
upstream scripts during an explicit image build, never in public CI.

Public CI checks shell syntax, deterministic staging and structural safety on
a standard GitHub-hosted runner. Passing it does not constitute an image build,
Kit conformance, runtime or cloud acceptance test.

Specifications: [Kit v3](https://github.com/docker/sandbox-kit-spec) and
[Kit v2](https://github.com/docker/sbx-kits-contrib/blob/main/spec/SPEC-v2.md).
