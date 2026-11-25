#!/usr/bin/env python3
"""Write the build list of the LineageOS Updater app from a released ROM zip.

The Lumia device trees point lineage.updater.uri at

    https://github.com/<repo>/releases/latest/download/ota

(a writable property holds at most 91 bytes, hence the name without an
extension), so this JSON file has to be uploaded as an asset of every
release, next to the zip it describes:

    tools/updater-json.py lineage-18.1-20261126-UNOFFICIAL-martini.zip \\
        --repo lumia-msm8974/android_device_nokia_martini \\
        --tag lineage-18.1-20261126-martini
    gh release upload lineage-18.1-20261126-martini ota \\
        -R lumia-msm8974/android_device_nokia_martini

GitHub serves "latest" from the release marked Latest, never from a
pre-release, so a build reaches the Updater only once it is promoted.

The Updater offers a build when "version" is not older than
ro.lineage.build.version, "romtype" equals ro.lineage.releasetype and
"datetime" is newer than ro.build.date.utc of the running system. The
datetime comes from post-timestamp in the zip metadata, which is the
ro.build.date.utc of the build inside the zip.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

NAME_RE = re.compile(r"^lineage-(?P<version>[0-9.]+)-(?P<date>[0-9]{8})-"
                     r"(?P<type>[A-Za-z]+)-(?P<device>[A-Za-z0-9_]+)\.zip$")


def read_metadata(zf):
    text = zf.read("META-INF/com/android/metadata").decode()
    meta = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            meta[key.strip()] = value.strip()
    return meta


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("zip", help="ROM zip exactly as it is attached to the release")
    ap.add_argument("--repo", required=True, help="GitHub owner/name that holds the release")
    ap.add_argument("--tag", required=True, help="release tag")
    ap.add_argument("--out", default="ota", help="output file (default ota, the asset name)")
    args = ap.parse_args()

    filename = os.path.basename(args.zip)
    m = NAME_RE.match(filename)
    if not m:
        sys.exit(f"{filename}: not a lineage-<version>-<date>-<type>-<device>.zip name; "
                 "the Updater shows and checks the name, keep the one the build made")

    with zipfile.ZipFile(args.zip) as zf:
        meta = read_metadata(zf)

    devices = meta.get("pre-device", "").split(",")
    if m["device"] not in devices:
        sys.exit(f"{filename}: the zip is for {meta.get('pre-device')}, not {m['device']}")
    try:
        timestamp = int(meta["post-timestamp"])
    except (KeyError, ValueError):
        sys.exit(f"{filename}: no post-timestamp in META-INF/com/android/metadata")

    digest = sha256_of(args.zip)
    entry = {
        "datetime": timestamp,
        "filename": filename,
        # Any unique string works; the hash also tells a re-uploaded zip apart.
        "id": digest,
        "romtype": m["type"],
        "size": os.path.getsize(args.zip),
        "url": f"https://github.com/{args.repo}/releases/download/{args.tag}/{filename}",
        "version": m["version"],
    }
    with open(args.out, "w") as f:
        json.dump({"response": [entry]}, f, indent=2)
        f.write("\n")
    print(f"{args.out}: {filename}, {entry['size']} bytes, datetime {timestamp}, "
          f"sha256 {digest[:16]}...")


if __name__ == "__main__":
    main()
