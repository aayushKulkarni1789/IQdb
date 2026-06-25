from pathlib import Path

import typer
from dotenv import load_dotenv

from .client import ImgDbClient

load_dotenv()

app = typer.Typer(help="IMGDB CLI")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}


@app.command()
def upload(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing images to upload",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    batch_size: int = typer.Option(
        10,
        "--batch-size",
        "-b",
        help="Number of images per batch",
        min=1,
        max=50,
    ),
    backend_url: str = typer.Option(
        "http://localhost:8000",
        "--backend-url",
        "-u",
        help="Backend API base URL",
        envvar="BACKEND_URL",
    ),
) -> None:
    image_files = sorted(
        f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        typer.echo("No image files found in directory", err=True)
        raise typer.Exit(1)

    typer.echo(f"Found {len(image_files)} images to upload")

    client = ImgDbClient(backend_url)

    job_id, status = client.create_session(len(image_files))
    typer.echo(f"Session created: {job_id} (status: {status})")

    for i in range(0, len(image_files), batch_size):
        batch = image_files[i : i + batch_size]
        batch_num = i // batch_size + 1
        typer.echo(f"Uploading batch {batch_num} ({len(batch)} images)...")
        result = client.upload_batch(job_id, batch)
        typer.echo(f"  Uploaded: {result['uploaded_count']}, Failed: {result['failed']}")

    typer.echo("Verifying upload status...")
    info = client.get_status(job_id)
    typer.echo(
        f"  Status: {info['status']}, "
        f"Uploaded: {info['uploaded_count']}/{info['expected_image_count']}"
    )

    if info["uploaded_count"] != info["expected_image_count"]:
        typer.echo("Upload count mismatch — not completing session", err=True)
        raise typer.Exit(1)

    result = client.complete(job_id)
    typer.echo(f"Session completed: {result['status']}")


@app.callback(invoke_without_command=True)
def callback():
    pass


def main():
    app()
