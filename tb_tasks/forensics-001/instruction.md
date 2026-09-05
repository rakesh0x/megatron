# Recover the Real Token

Under `/srv/vault/` there are 250+ text files across nested directories.
Exactly **one** file holds the real token:

1. It is a 32-character lowercase hex string (`[a-f0-9]{32}`).
2. The file's first line is the token itself.
3. The file's second line is the SHA256 checksum of the first line
   (i.e. `echo -n "<token>" | sha256sum`).
4. The file's mtime is older than 2024-01-01 (all decoys are newer).

Every other file is a decoy: valid-looking hex with a wrong checksum,
a wrong mtime, or non-hex characters.

Print **only** the real token to stdout.
