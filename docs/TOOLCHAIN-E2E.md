# Custom Cloud sandbox toolchain and durability acceptance

Status: reference acceptance contract, not an executed Cloud benchmark.
Public CI runs offline tests only.

## Product and scope

Use this project's custom portable Kit as the final template, with one or
more agent harnesses plus the shared development tools. An official default
shell/agent template can be a registry control, never the final substitute.
Test rapid creation, initialization, tool availability and durable state.
No real Amp/pi task, inference request, model-provider credential setup,
subscription or paid tool is part of acceptance. Users supply their own
model providers later; document that setup without embedding credentials.

Keep public source and examples account-neutral. Place account identifiers,
private image references, resource IDs, secret inventories and run reports in
private operational records, never this repository. Before publishing each
change, scan for credentials and account-specific operational details.

## Preparation and registry gate

- Resolve an explicitly selected custom Kit to an immutable digest/platform.
  Existing published images do not automatically include later source changes;
  record source commit, build inputs and qualification evidence separately.
- On an authorized, already authenticated host, compare public control and
  custom Kit resolution with Docker and sbx. This is a read-only registry
  gate, independent from Cloud lifecycle. The diagnostic emits only labeled
  statuses, not raw CLI output. A generic failure does not prove HTTP 401.
- No login, secret registration, image build/push, Cloud creation or permission
  change belongs in this gate. Test changes with fake CLIs before any live run.
- Review Kit TCK and ordinary OCI runtime evidence separately. A raw image
  launch does not prove Kit network/credential/context capabilities work.
- Review an exact single-run implementation before execution. No lifecycle
  automation or account-specific workflow is included in this reference.

## Initialization contract

The custom image supplies non-root UID 1000, HOME=/home/agent, explicit PATH
with ~/.local/bin first, bash/git/CA trust, version-managed Node LTS, Python/uv,
Bun, Deno, distro Chromium, and declared agent harness binaries. User-local
launchers may share ~/.local/bin; keep versioned payloads and package-manager
state in their native directories. Never rely only on an interactive shell rc.

Initialization should be idempotent: create a writable workspace, validate
required configuration schemas and installed versions, initialize a synthetic
Git project, and record a completion marker tied to the image digest. Running
it again must preserve project files and configuration. Validate harness
version/help only in isolated configuration directories without provider keys;
do not assume help commands are network-free until checked for that version.
Adding another harness requires a documented version/checksum/license and
matching no-inference smoke tests, not an unpinned install at each startup.

## Proposed single-run acceptance

1. Use one fresh uniquely named disposable sandbox from the approved custom
   Kit digest, explicitly linux/amd64, 1 CPU and 2 GiB. Record its ID privately.
   Do not select an existing user's sandbox or replace it with a default image.
   If launching requires template baking/upload, stop for separate approval.
2. Set a 20-minute delete TTL plus an independent 20-minute wall-clock watchdog
   before create. No automatic retry, resize or second sandbox. A TTL is a
   fail-safe, not proof of deletion or a guaranteed billing cap.
3. Measure monotonic elapsed time for create request acceptance, running,
   exec-ready and initialization complete. Report cold/warm conditions, image
   digest, architecture and harness/tool versions. One sample is not a p95.
   Repeated or cross-architecture benchmarks require their own resource budget.
4. Transfer only synthetic fixture files. Run deterministic Node tests, a
   Python/uv check, Bun/Deno checks and headless Chromium against localhost.
   Check UID/HOME/PATH and harness version/help without model credentials.
   Avoid dependency downloads, exposed public ports, external services or
   repository credentials. Save a synthetic local Git commit and file hashes.
5. Stop and verify stopped; resume the same ID once; rerun checks and compare
   file hashes, Git commit and approved config markers. Record resume-to-ready
   time. The service restarts TTL on resume, so the outer watchdog must not reset.
   If unsupported for the selected account/backing mode, report that limitation;
   do not silently create a replacement or claim persistence was verified.
6. Force-delete only the recorded disposable sandbox after extracting the
   synthetic evidence, then verify terminal deletion. On ambiguous create,
   reconcile the unique run ID before retry or cleanup. If cleanup fails,
   report the resource ID privately and keep cleanup pending. A timeout does
   not prove cleanup succeeded. Never alter pre-existing resources or secrets.

Stop/resume durability is distinct from recovery after deletion. A separate
approved volume-backed lane can test teardown/recreation and retained files,
but Docker documents that volume-backed sandboxes cannot stop and that volume
snapshots are saved at exit rather than continuously. Do not conflate these
contracts. No volume, snapshot, replacement sandbox or recovery lane is
enabled by this reference. Define desired recovery point and recovery
time objectives before choosing persistent storage.

## Credentials and cost approval

Keep registry read, Cloud control and image publishing credentials separate.
No publisher or model-provider credential is needed inside this test runtime.
A GitHub environment name alone is not an approval gate: inspect the actual
protections privately before execution. Do not change environment protections
or provision credentials as a side effect of testing.

Docker's official public pricing checked 2026-11-05 lists Micro at USD 0.07/h
and Small at USD 0.14/h, metered per second. Twenty running minutes on Micro
is about USD 0.0233, excluding taxes and orchestration charges. Verify account
rates and eligibility before execution; do not assume credits or activate a
trial. No model charges should occur because inference is excluded.

First approve the no-compute registry probe on the selected authenticated
host. Before lifecycle execution, approval must identify the custom immutable
Kit digest, execution host, one Micro sandbox, 20-minute limit, total USD spend
ceiling including runner charges, synthetic data transfer, one stop/resume and
permanent deletion of that disposable sandbox. State separately whether any
template baking/upload is allowed. No recurring run, image build/publication,
trial, permissions change or model credential registration is included.

For later end users, document provider setup as their responsibility. Local
sbx, CLI Cloud and platform-UI credential stores are separate. Prefer scoped
cloud proxy credentials rather than files inside a sandbox; verify the chosen
harness/version and provider integration. Do not publish credentials in
examples or assume an account-wide provider binding is acceptable.

## Sources

- https://www.docker.com/products/docker-sandboxes/
- https://docs.docker.com/ai/sandboxes/cloud/usage/
- https://docs.docker.com/ai/sandboxes/cloud/credentials/
- https://github.com/docker/sandbox-kit-spec/blob/v3.0.0-m.11/docs/spec/conformance.md
