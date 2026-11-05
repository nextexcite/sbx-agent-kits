"""Exercise the read-only diagnostic using fake CLIs, never a registry."""
from pathlib import Path
import os
import signal
import sys
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnose-kit-registry.sh"


class RegistryDiagnosticTests(unittest.TestCase):
    def fixture(self, args=("registry.example/fixture/image:test",), docker_status=0, sbx_status=0, seconds="1", hang=False,
                traced=False, descendant=False, launcher_exits=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            log = path / "calls"
            (path / "python3").symlink_to(sys.executable)
            helper_pid = path / "helper.pid"
            (path / "helper.py").write_text(
                'import os, signal, time\n'
                'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                'open(os.environ["HELPER_PID"], "w").write(str(os.getpid()))\n'
                'while True: time.sleep(1)\n'
            )
            for cli, status in (("docker", docker_status), ("sbx", sbx_status)):
                binary = path / cli
                binary.write_text(
                    '#!/bin/bash\nprintf "%s\\n" "$0 $*" >> "$CALL_LOG"\n'
                    'echo fixture-secret-stdout\necho fixture-secret-stderr >&2\n'
                    + ('trap "" TERM\nwhile :; do :; done\n' if hang and cli == "docker" else '')
                    + (('trap "exit 0" TERM\npython3 "$HELPER_SCRIPT" &\n'
                        'while [[ ! -f "$HELPER_PID" ]]; do :; done\n'
                        + ('exit 0\n' if launcher_exits else 'wait\n'))
                       if descendant and cli == "docker" else '')
                    + 'case "${!#}" in *public*) exit 0;; esac\n'
                    + f'exit {status}\n'
                )
                binary.chmod(0o700)
            started = time.monotonic()
            result = subprocess.run(
                ["/bin/bash", *(["-x"] if traced else []), str(SCRIPT), *args],
                env={"PATH": directory, "CALL_LOG": str(log),
                     "REGISTRY_PROBE_TIMEOUT_SECONDS": seconds,
                     "HELPER_PID": str(helper_pid), "HELPER_SCRIPT": str(path / "helper.py")},
                capture_output=True, text=True, timeout=8,
            )
            elapsed = time.monotonic() - started
            if descendant:
                self.assertTrue(helper_pid.exists(), "helper did not start")
                pid = int(helper_pid.read_text())
                # An orphan can briefly remain a zombie until PID 1 reaps it;
                # zombies cannot execute or retain network activity.
                live = False
                for _ in range(100):
                    try:
                        state = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0]
                    except FileNotFoundError:
                        break
                    if state == "Z":
                        break
                    time.sleep(0.01)
                else:
                    live = True
                if live:
                    os.kill(pid, signal.SIGKILL)
                self.assertFalse(live, "resolver helper survived process-group cleanup")
            self.assertNotIn("fixture-secret", result.stdout + result.stderr)
            calls = log.read_text().splitlines() if log.exists() else []
            return result, calls, elapsed

    def test_both_resolvers_run_and_either_failure_fails_preflight(self):
        for docker_status, sbx_status in ((0, 0), (1, 0), (0, 1), (1, 1)):
            with self.subTest(docker=docker_status, sbx=sbx_status):
                ref = "docker.io/example/private:fixture"
                result, calls, _ = self.fixture([ref], docker_status, sbx_status)
                self.assertEqual(result.returncode, int(bool(docker_status or sbx_status)))
                self.assertEqual(len(calls), 2)
                self.assertTrue(calls[0].endswith(f"/docker buildx imagetools inspect {ref}"))
                self.assertTrue(calls[1].endswith(f"/sbx kit inspect {ref}"))
                self.assertIn("target docker " + ("FAIL exit=1" if docker_status else "PASS"), result.stdout)
                self.assertIn("target sbx " + ("FAIL exit=1" if sbx_status else "PASS"), result.stdout)
                self.assertNotIn(ref, result.stdout + result.stderr)

    def test_comparison_keeps_private_and_public_results_separate(self):
        result, calls, _ = self.fixture(
            ["--compare", "docker.io/example/private:fixture", "docker.io/example/public:fixture"],
            docker_status=1, sbx_status=1,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 4)
        for line in ("private docker FAIL exit=1", "private sbx FAIL exit=1",
                     "public docker PASS", "public sbx PASS"):
            self.assertIn(line, result.stdout)
        self.assertNotIn("docker.io", result.stdout + result.stderr)

    def test_timeout_kills_uncooperative_cli_and_still_runs_other_resolver(self):
        result, calls, elapsed = self.fixture(hang=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("target docker TIMEOUT", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertIn("target sbx PASS", result.stdout)
        self.assertEqual(len(calls), 2)
        self.assertLess(elapsed, 5)

    def test_trace_does_not_reveal_reference_or_cli_output(self):
        ref = "docker.io/example/private:fixture"
        result, _, _ = self.fixture([ref], traced=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(ref, result.stdout + result.stderr)

    def test_invalid_timeout_or_arguments_fail_before_cli_execution(self):
        for seconds in ("0", "61", "-1", "1s", "999999", "1;echo secret"):
            with self.subTest(seconds=seconds):
                result, calls, _ = self.fixture(seconds=seconds)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])
        for args in ([], ["--compare"], ["one", "two"], ["--debug"], ["bad\nref"]):
            with self.subTest(args=args):
                result, calls, _ = self.fixture(args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])

    def test_missing_cli_fails_without_network(self):
        for missing in ("docker", "sbx", "python3"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                for cli in ("docker", "sbx", "python3"):
                    if cli != missing:
                        available = Path(directory) / cli
                        available.write_text("#!/bin/bash\nexit 99\n")
                        available.chmod(0o700)
                result = subprocess.run(
                    ["/bin/bash", str(SCRIPT)], env={"PATH": directory},
                    capture_output=True, timeout=5,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")

    @unittest.skipUnless(sys.platform.startswith("linux"), "uses /proc to distinguish zombies")
    def test_timeout_kills_helper_after_launcher_exits_on_term(self):
        result, calls, elapsed = self.fixture(descendant=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("target docker TIMEOUT", result.stdout)
        self.assertIn("target sbx PASS", result.stdout)
        self.assertEqual(len(calls), 2)
        self.assertLess(elapsed, 5)

    @unittest.skipUnless(sys.platform.startswith("linux"), "uses /proc to distinguish zombies")
    def test_normal_launcher_exit_also_cleans_background_helper(self):
        result, calls, elapsed = self.fixture(descendant=True, launcher_exits=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("target docker PASS", result.stdout)
        self.assertEqual(len(calls), 2)
        self.assertLess(elapsed, 4)

    @unittest.skipUnless(sys.platform.startswith("linux"), "uses /proc to distinguish zombies")
    def test_wrapper_interrupts_clean_child_process_group(self):
        wrapper = ROOT / "scripts/probe-with-timeout.py"
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory() as directory:
                pid_file = Path(directory) / "pid"
                child = (
                    'import os, signal, time; '
                    'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                    f'open({str(pid_file)!r}, "w").write(str(os.getpid())); '
                    'time.sleep(30)'
                )
                process = subprocess.Popen(
                    [sys.executable, str(wrapper), "60", sys.executable, "-c", child],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                pid = None
                try:
                    for _ in range(200):
                        if pid_file.exists() and pid_file.read_text():
                            pid = int(pid_file.read_text())
                            break
                        time.sleep(0.01)
                    self.assertIsNotNone(pid, "child did not start")
                    process.send_signal(signum)
                    stdout, stderr = process.communicate(timeout=4)
                    self.assertEqual(process.returncode, 128 + signum)
                    self.assertEqual((stdout, stderr), (b"", b""))
                    self.assertFalse(Path(f"/proc/{pid}").exists(), "direct child not reaped")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    if pid is not None:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_interrupt_exit_codes_abort_remaining_comparison_probes(self):
        args = ["--compare", "registry.example/fixture/private:test",
                "registry.example/fixture/public:test"]
        for code in (130, 143):
            for resolver in ("docker", "sbx"):
                with self.subTest(code=code, resolver=resolver):
                    result, calls, _ = self.fixture(
                        args, docker_status=code if resolver == "docker" else 0,
                        sbx_status=code if resolver == "sbx" else 0,
                    )
                    self.assertEqual(result.returncode, code)
                    self.assertEqual(len(calls), 1 if resolver == "docker" else 2)
                    self.assertIn(f"private {resolver} INTERRUPTED", result.stdout)
                    self.assertNotIn("public ", result.stdout)
                    self.assertNotIn("checks finished", result.stdout)

    def test_real_wrapper_interrupt_aborts_shell_without_later_probes(self):
        for signum, target in ((signal.SIGINT, "wrapper"), (signal.SIGTERM, "wrapper"),
                               (signal.SIGINT, "diagnostic-group")):
            with self.subTest(signal=signum, target=target), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "python3").symlink_to(sys.executable)
                log, pids = path / "calls", path / "pids"
                for cli in ("docker", "sbx"):
                    binary = path / cli
                    binary.write_text(
                        '#!/bin/bash\nprintf "%s\\n" "' + cli + '" >> "$CALL_LOG"\n'
                        + ('case "${!#}" in *public*) exit 0;; esac\n'
                           'trap "" TERM\nprintf "%s %s\\n" "$PPID" "$$" > "$PIDS"\n'
                           'while :; do :; done\n' if cli == "docker" else 'exit 0\n')
                    )
                    binary.chmod(0o700)
                process = subprocess.Popen(
                    ["/bin/bash", str(SCRIPT), "--compare",
                     "registry.example/fixture/private:test", "registry.example/fixture/public:test"],
                    env={"PATH": directory, "CALL_LOG": str(log), "PIDS": str(pids),
                         "REGISTRY_PROBE_TIMEOUT_SECONDS": "60"},
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                )
                wrapper_pid = child_pid = None
                try:
                    for _ in range(200):
                        if pids.exists() and len(pids.read_text().split()) == 2:
                            wrapper_pid, child_pid = map(int, pids.read_text().split())
                            break
                        time.sleep(0.01)
                    self.assertIsNotNone(wrapper_pid, "resolver wrapper did not start")
                    if target == "diagnostic-group":
                        os.killpg(process.pid, signum)
                    else:
                        os.kill(wrapper_pid, signum)
                    stdout, stderr = process.communicate(timeout=4)
                    self.assertEqual(process.returncode, 128 + signum)
                    self.assertEqual(log.read_text().splitlines(), ["docker"])
                    self.assertEqual(stdout, "private docker INTERRUPTED\n")
                    self.assertEqual(stderr, "")
                    with self.assertRaises(ProcessLookupError):
                        os.kill(child_pid, 0)
                finally:
                    # Clean test-owned processes even when the regression fails.
                    for pid in (child_pid, wrapper_pid):
                        if pid is not None:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()

    @unittest.skipUnless(sys.platform.startswith("linux"), "uses /proc to distinguish zombies")
    def test_cancellation_during_cleanup_stops_remaining_probes(self):
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "python3").symlink_to(sys.executable)
                log, ready, cleanup, pid_file, wrapper_file = [path / n for n in ("calls", "ready", "cleanup", "pid", "wrapper")]
                helper = path / "helper.py"
                helper.write_text(
                    'import os, signal, time\n'
                    'def term(*_):\n'
                    '    open(os.environ["CLEANUP"], "w").write("started")\n'
                    'signal.signal(signal.SIGTERM, term)\n'
                    'open(os.environ["PID_FILE"], "w").write(str(os.getpid()))\n'
                    'open(os.environ["READY"], "w").write("ready")\n'
                    'while True: time.sleep(1)\n'
                )
                for cli in ("docker", "sbx"):
                    binary = path / cli
                    binary.write_text(
                        '#!/bin/bash\nprintf "%s\\n" "' + cli + '" >> "$CALL_LOG"\n'
                        + ('printf "%s\\n" "$PPID" > "$WRAPPER_FILE"\npython3 "$HELPER" &\nwhile [[ ! -f "$READY" ]]; do :; done\n'
                           if cli == "docker" else '') + 'exit 0\n'
                    )
                    binary.chmod(0o700)
                process = subprocess.Popen(
                    ["/bin/bash", str(SCRIPT), "--compare", "registry.example/private:test",
                     "registry.example/public:test"],
                    env={"PATH": directory, "CALL_LOG": str(log), "HELPER": str(helper),
                         "READY": str(ready), "CLEANUP": str(cleanup), "PID_FILE": str(pid_file),
                         "WRAPPER_FILE": str(wrapper_file)},
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                )
                helper_pid = None
                try:
                    deadline = time.monotonic() + 3
                    while not cleanup.exists() and time.monotonic() < deadline:
                        time.sleep(0.005)
                    self.assertTrue(cleanup.exists(), "cleanup phase did not start")
                    helper_pid = int(pid_file.read_text())
                    if signum == signal.SIGINT:
                        os.killpg(process.pid, signum)
                    else:
                        # The wrapper shares the shell group, but SIGTERM directly
                        # to the shell would terminate it before it can print status.
                        os.kill(int(wrapper_file.read_text()), signum)
                    stdout, stderr = process.communicate(timeout=4)
                    self.assertEqual(process.returncode, 128 + signum)
                    self.assertEqual(log.read_text().splitlines(), ["docker"])
                    self.assertEqual(stdout, "private docker INTERRUPTED\n")
                    self.assertEqual(stderr, "")
                    stat = Path(f"/proc/{helper_pid}/stat")
                    if stat.exists():
                        self.assertEqual(stat.read_text().split(") ", 1)[1][0], "Z")
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    if helper_pid is not None:
                        try:
                            os.kill(helper_pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
