import lzma
import subprocess
from configparser import ConfigParser
from io import BytesIO
from pathlib import Path
from shutil import rmtree
from concurrent.futures import ProcessPoolExecutor

import requests
from PIL import Image
from sh import mount, umount  # type: ignore
from sh.contrib import sudo  # type: ignore

CTGP = Path("ctgp")
OUT = Path("./out")
IN = Path("./in")

CTGP_ROOT = CTGP / "PACKAGES" / "CTGPR"
CTGP_TRACKS = CTGP_ROOT / "RACE" / "COURSE"

TRACKS = OUT / "tracks"
THUMBNAILS = OUT / "thumbnails"
TEMP_TRACKS = OUT / "temp tracks"

def find_track_id(trackManifest: ConfigParser, sha1: str) -> str | None:
    for track in trackManifest.sections():
        if trackManifest[track]["sha1"] == sha1:
            return track

def fetch_thumbnail(track_id: str):
    if (THUMBNAILS / f"{track_id}.jpg").exists():
        return

    resp = requests.get(f"http://archive.tock.eu/fullpreview/{track_id[-2:]}/{track_id}.jpg")
    if resp.status_code != 404:
        resp.raise_for_status()

        thumbnail = Image.open(BytesIO(resp.content))
        thumbnail = thumbnail.resize((256, 144))
        thumbnail.save(THUMBNAILS / f"{track_id}.jpg")

def recompress_track(track: Path, track_id: str):
    subprocess.run(["wszst", "decompress", "--u8", track, "-d", TEMP_TRACKS / f"{track_id}.u8"])

    u8_file = TEMP_TRACKS / f"{track_id}.u8"
    lzma_file = TRACKS / f"{track_id}.arc.lzma"
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
        sha1 = subprocess.run(["wszst", "sha1", track], capture_output=True).stdout.decode().split(" ")[0]
        track_id = find_track_id(trackManifest, sha1)

        if track_id is not None:
            manifest["Pack Info"]["race"] += f"{track_id},"
            track_id = track_id.rjust(5, "0")

            pool.submit(recompress_track, track, track_id)
            pool.submit(fetch_thumbnail, track_id)
        else:
            print(f"Warning: Could not find track with sha1 {sha1}!")

    with open(OUT / "manifest.ini", "w") as f:
        manifest.write(f)

if __name__ == "__main__":
    with sudo:
        with ProcessPoolExecutor() as pool:
            try:
                main(pool)
            finally:
                cleanup()
