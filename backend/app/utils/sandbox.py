import os
import subprocess
from pathlib import Path

# Minimal environment so a compromised/malicious LaTeX payload can't ride
# along on the parent process's credentials, tokens, etc.
_ALLOWED_ENV_KEYS = {"PATH", "HOME"}


def run_sandboxed(cmd: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with a stripped-down env, a hard timeout, and its cwd
    confined to the given directory. Full OS-level sandboxing (network
    namespace isolation, container confinement) is deferred to the
    hardening milestone / infra/docker — this covers the cheap, load-bearing
    protections (timeout, minimal env, no ambient network via tectonic's
    --only-cached flag)."""
    env = {key: os.environ[key] for key in _ALLOWED_ENV_KEYS if key in os.environ}
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
