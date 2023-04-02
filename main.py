from io import BytesIO
import subprocess
from configparser import ConfigParser
from pathlib import Path
from PIL import Image

import requests
from os import mkdir
from sh import cp, mount, rm, umount  # type: ignore
from sh.contrib import sudo  # type: ignore

CTGP_MOUNT = Path("ctgp")
OUT = Path("./out")
IN = Path("./in")

CTGP_ROOT = CTGP_MOUNT / "PACKAGES" / "CTGPR"
CTGP_TRACKS = CTGP_ROOT / "RACE" / "COURSE"

THUMBNAILS = OUT / "thumbnails"

def find_track_id(trackManifest: ConfigParser, sha1: str) -> str | None:
    for track in trackManifest.sections():
        if trackManifest[track]["sha1"] == sha1:
            return track

    print(f"\nWarning: Could not find track with sha1 {sha1}")

def fetch_thumbnail(track_id: str):
    if (THUMBNAILS / f"{track_id}.jpg").exists():
        return

    resp = requests.get(f"http://archive.tock.eu/fullpreview/{track_id[-2:]}/{track_id}.jpg")
    if resp.status_code != 404:
        resp.raise_for_status()

        thumbnail = Image.open(BytesIO(resp.content))
        thumbnail = thumbnail.resize((256, 144))
        thumbnail.save(THUMBNAILS / f"{track_id}.jpg")

def cleanup():
    if CTGP_MOUNT.exists():
        umount(CTGP_MOUNT)
        rm(CTGP_MOUNT, r=True)

def main():
    if not Path(OUT / "blob.dat").exists():
        import decrypter

        decrypter.run(
            open(IN / "blob.bin", "rb"),
            open(OUT / "blob.dat", "wb"),
            encode=False
        )

    if not (OUT / "tracks").exists():
        mkdir(OUT / "tracks")

    if not THUMBNAILS.exists():
        mkdir(THUMBNAILS)

    mount(OUT / "blob.dat", CTGP_MOUNT, mkdir=True)

    trackManifest = ConfigParser()
    trackManifest.read(IN / "tracks.ini")

    manifest = ConfigParser()
    manifest["Pack Info"] = {
        "name": "Custom Track Grand Prix",
        "author": "Mr Bean35000vr & Chadderz",
        "description": "A custom track pack for Mario Kart Wii",

        "race": "",
    }

    for i, track in enumerate(CTGP_TRACKS.glob("*.SZS")):
        sha1 = subprocess.run(["wszst", "sha1", track], capture_output=True).stdout.decode().split(" ")[0]
        track_id = find_track_id(trackManifest, sha1)

        if track_id is not None:
            cp(track, OUT / "tracks" / f"{track_id}.szs")
            manifest["Pack Info"]["race"] += f"{track_id},"

            track_id = track_id.rjust(5, "0")
            fetch_thumbnail(track_id)

            print(f"Found track {track_id} ({i})", end="\r")

    with open(OUT / "manifest.ini", "w") as f:
        manifest.write(f)

if __name__ == "__main__":
    with sudo:
        try:
            main()
        finally:
            cleanup()
