import lzma
import subprocess
from configparser import ConfigParser
from io import BytesIO, IOBase
from pathlib import Path
from shutil import rmtree
from concurrent.futures import ProcessPoolExecutor

import requests
from PIL import Image
from sh import mount, umount  # type: ignore
from sh.contrib import sudo  # type: ignore

from unreleased_tracks import UNRELEASED_TRACKS

CTGP = Path("ctgp")
OUT = Path("./out")
IN = Path("./in")

CTGP_ROOT = CTGP / "PACKAGES" / "CTGPR"
CTGP_TRACKS = CTGP_ROOT / "RACE" / "COURSE"

TRACKS = OUT / "tracks"
THUMBNAILS = OUT / "thumbnails"
TEMP_TRACKS = OUT / "temp tracks"

def process_thumbnail(sha1: str, raw: IOBase):
    image = Image.open(raw)
    image = image.resize((256, 144))
    image.save(THUMBNAILS / f"{sha1}.jpg")

def find_track_id(trackManifest: ConfigParser, sha1: str) -> str | None:
    for track_sha1 in trackManifest.sections():
        if track_sha1 == sha1:
            return trackManifest[sha1]["id"]

def fetch_thumbnail(track_id: str, sha1: str):
    track_id = track_id.rjust(5, "0")
    if (THUMBNAILS / f"{track_id}.jpg").exists():
        return

    resp = requests.get(f"http://archive.tock.eu/fullpreview/{track_id[-2:]}/{track_id}.jpg")
    if resp.status_code == 404:
        backup_thumbnail = Path(f"thumbnails/{sha1}.png")
        if not backup_thumbnail.exists():
            return

        with open(backup_thumbnail, "rb") as f:
            resp_bytes = f.read()
    else:
        resp.raise_for_status()
        resp_bytes = resp.content

    process_thumbnail(sha1, BytesIO(resp_bytes))

def recompress_track(track: Path, sha1: str):
    subprocess.run(["wszst", "decompress", "--u8", track, "-d", TEMP_TRACKS / f"{sha1}.u8"])

    u8_file = TEMP_TRACKS / f"{sha1}.u8"
    lzma_file = TRACKS / f"{sha1}.arc.lzma"
    with open(u8_file, "rb") as f:
        with lzma.open(lzma_file, "wb", format=lzma.FORMAT_ALONE) as g:
            print(f"RECOMPRESS U8:{u8_file} -> {lzma_file}")
            g.write(f.read())

def cleanup():
    if CTGP.exists():
        umount(CTGP)
        rmtree(CTGP)

def main(pool: ProcessPoolExecutor):
    for folder in (TRACKS, TEMP_TRACKS):
        rmtree(folder, ignore_errors=True)

    for folder in (OUT, CTGP, TRACKS, THUMBNAILS, TEMP_TRACKS):
        folder.mkdir(exist_ok=True)

    if not Path(OUT / "blob.dat").exists():
        import decrypter

        decrypter.run(
            open(IN / "blob.bin", "rb"),
            open(OUT / "blob.dat", "wb"),
            encode=False
        )

    mount(OUT / "blob.dat", CTGP)

    trackManifest = ConfigParser()
    trackManifest.read(IN / "tracks.ini")

    manifest = ConfigParser()
    manifest["Pack Info"] = {
        "name": "Custom Track Grand Prix",
        "author": "Mr Bean35000vr & Chadderz",
        "description": "A custom track pack for Mario Kart Wii",

        "race": "",
    }

    for track in CTGP_TRACKS.glob("*.SZS"):
        sha1 = subprocess.run(["wszst", "sha1", "--norm", track], capture_output=True).stdout.decode().split(" ")[0]
        track_id = find_track_id(trackManifest, sha1)

        if track_id is not None:
            pool.submit(fetch_thumbnail, track_id, sha1)
        elif (unreleased_info := UNRELEASED_TRACKS.get(sha1)) is not None:
            manifest[sha1] = {
                "trackname": unreleased_info.name,
                "slot": str(unreleased_info.slot),
                "ctype": "1"
            }

            try:
                with open(f"thumbnails/{sha1}.png", "rb") as f:
                    raw = f.read()
            except FileNotFoundError:
                print(f"Warning: Could not find thumbnail for {sha1}")
            else:
                process_thumbnail(sha1, BytesIO(raw))
        else:
            continue

        manifest["Pack Info"]["race"] += f"{sha1},"
        pool.submit(recompress_track, track, sha1)

    with open(OUT / "manifest.ini", "w") as f:
        manifest.write(f)

if __name__ == "__main__":
    with sudo:
        try:
            with ProcessPoolExecutor() as pool:
                main(pool)
        finally:
            cleanup()
