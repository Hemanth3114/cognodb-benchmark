from pathlib import Path
import gzip
import shutil
import urllib.request


DATA_DIR = Path("data")
ARCHIVE_PATH = DATA_DIR / "email-Eu-core-temporal.txt.gz"
OUTPUT_PATH = DATA_DIR / "email_edges.csv"

DATA_URL = (
    "https://snap.stanford.edu/data/email-Eu-core-temporal.txt.gz"
)


def download_dataset():
    DATA_DIR.mkdir(exist_ok=True)

    if not ARCHIVE_PATH.exists():
        print("Downloading SNAP email-Eu-core temporal dataset...")
        urllib.request.urlretrieve(DATA_URL, ARCHIVE_PATH)
        print("Download complete.")
    else:
        print("Dataset archive already exists.")


def convert_to_csv():
    if OUTPUT_PATH.exists():
        print("CSV file already exists.")
        return

    print("Converting dataset to CSV...")

    with gzip.open(ARCHIVE_PATH, "rt", encoding="utf-8") as source:
        with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as target:
            target.write("source_id,target_id,timestamp\n")

            for line in source:
                line = line.strip()

                if not line:
                    continue

                source_id, target_id, timestamp = line.split()

                target.write(
                    f"{source_id},{target_id},{timestamp}\n"
                )

    print("CSV conversion complete.")


if __name__ == "__main__":
    download_dataset()
    convert_to_csv()