"""Stands in for ssh in tests.

It drops the host and runs the remote command with sh, as sshd does. If
FAKE_SSH_KEY names a public key, and that key's line in
$HOME/.ssh/authorized_keys has a forced command, it runs the forced command
instead and sets SSH_ORIGINAL_COMMAND, as sshd does.
"""

import os
import sys
from pathlib import Path

from rbeets.authkeys import forced_command_for, parse_public_key

command = " ".join(sys.argv[2:])
key_path = os.environ.get("FAKE_SSH_KEY")
if key_path:
    authorized = Path.home() / ".ssh" / "authorized_keys"
    key = parse_public_key(Path(key_path).read_text())
    forced = forced_command_for(authorized.read_bytes(), key)
    if forced is not None:
        os.environ["SSH_ORIGINAL_COMMAND"] = command
        command = forced
os.execvp("sh", ["sh", "-c", command])
