import logging
from pathlib import Path

import click

from etsy_assistant.config import PipelineConfig
from etsy_assistant.pipeline import process_image
from etsy_assistant.steps.keywords import generate_listing, save_metadata

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def _setup_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Etsy Assistant - Image processing for pen & ink sketch artists."""


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), default=None,
              help="Output file or directory.")
@click.option("-s", "--size", "sizes", multiple=True,
              help="Print size (5x7, 8x10, 11x14, 16x20, A4). Repeatable.")
@click.option("--dpi", default=300, show_default=True, help="Output DPI.")
@click.option("--skip", "skip_steps", multiple=True,
              help="Skip step (autocrop, perspective, background, contrast). Repeatable.")
@click.option("--no-perspective", is_flag=True, help="Skip perspective correction.")
@click.option("--debug", is_flag=True, help="Save intermediate images for each step.")
@click.option("-v", "--verbose", is_flag=True, help="Debug logging.")
@click.option("-q", "--quiet", is_flag=True, help="Only show errors.")
def process(input_path, output_path, sizes, dpi, skip_steps, no_perspective, debug, verbose, quiet):
    """Process a single sketch photo into print-ready images."""
    _setup_logging(verbose, quiet)

    skip = set(skip_steps)
    if no_perspective:
        skip.add("perspective")

    config = PipelineConfig(output_dpi=dpi)

    if output_path is None:
        if sizes:
            output_path = input_path.parent / "output"
        else:
            output_path = input_path.with_stem(input_path.stem + "_clean")

    results = process_image(
        input_path=input_path,
        output_path=output_path,
        sizes=list(sizes) if sizes else None,
        config=config,
        skip_steps=skip,
        debug=debug,
    )

    for path in results:
        click.echo(f"✓ {path}")


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-o", "--output", "output_dir", type=click.Path(path_type=Path), default=None,
              help="Output directory (default: <directory>/output).")
@click.option("-s", "--size", "sizes", multiple=True,
              help="Print size. Repeatable.")
@click.option("--dpi", default=300, show_default=True)
@click.option("--skip", "skip_steps", multiple=True)
@click.option("--no-perspective", is_flag=True)
@click.option("--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
def batch(directory, output_dir, sizes, dpi, skip_steps, no_perspective, debug, verbose, quiet):
    """Process all images in a directory."""
    _setup_logging(verbose, quiet)

    skip = set(skip_steps)
    if no_perspective:
        skip.add("perspective")

    config = PipelineConfig(output_dpi=dpi)
    output_dir = output_dir or directory / "output"

    images = sorted(
        p for p in directory.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith(".")
    )

    if not images:
        click.echo(f"No images found in {directory}")
        return

    click.echo(f"Processing {len(images)} images...")
    for img_path in images:
        try:
            results = process_image(
                input_path=img_path,
                output_path=output_dir / (img_path.stem + "_clean.png"),
                sizes=list(sizes) if sizes else None,
                config=config,
                skip_steps=skip,
                debug=debug,
            )
            for path in results:
                click.echo(f"✓ {path}")
        except Exception as e:
            click.echo(f"✗ {img_path.name}: {e}", err=True)

    click.echo("Done.")


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
def info(input_path):
    """Display image metadata."""
    from PIL import Image

    img = Image.open(input_path)
    dpi = img.info.get("dpi", ("N/A", "N/A"))
    w, h = img.size

    click.echo(f"File:       {input_path}")
    click.echo(f"Format:     {img.format}")
    click.echo(f"Mode:       {img.mode}")
    click.echo(f"Size:       {w} x {h} px")
    click.echo(f"DPI:        {dpi[0]} x {dpi[1]}")
    if dpi != ("N/A", "N/A"):
        click.echo(f"Print size: {w / dpi[0]:.1f}\" x {h / dpi[1]:.1f}\"")
    click.echo(f"File size:  {input_path.stat().st_size / 1024:.0f} KB")


@main.command("generate-listing")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), default=None,
              help="Output path for processed image (default: <input>_clean.png).")
@click.option("-s", "--size", "sizes", multiple=True,
              help="Print size (5x7, 8x10, 11x14, 16x20, A4). Repeatable.")
@click.option("--dpi", default=300, show_default=True, help="Output DPI.")
@click.option("--skip", "skip_steps", multiple=True,
              help="Skip processing step. Repeatable.")
@click.option("--no-perspective", is_flag=True, help="Skip perspective correction.")
@click.option("--skip-processing", is_flag=True,
              help="Skip image processing, use input image directly for listing generation.")
@click.option("--model", default="claude-sonnet-4-20250514", show_default=True,
              help="Claude model for listing generation.")
@click.option("--json-output", "json_out", is_flag=True,
              help="Output listing metadata as JSON.")
@click.option("--save", "save_json", is_flag=True,
              help="Save listing metadata as a JSON sidecar file next to the image.")
@click.option("-v", "--verbose", is_flag=True, help="Debug logging.")
@click.option("-q", "--quiet", is_flag=True, help="Only show errors.")
def generate_listing_cmd(input_path, output_path, sizes, dpi, skip_steps,
                         no_perspective, skip_processing, model, json_out, save_json,
                         verbose, quiet):
    """Process a sketch and generate an Etsy listing (title, tags, description)."""
    import json as json_mod

    _setup_logging(verbose, quiet)

    if skip_processing:
        processed_path = input_path
    else:
        skip = set(skip_steps)
        if no_perspective:
            skip.add("perspective")

        config = PipelineConfig(output_dpi=dpi)

        if output_path is None:
            output_path = input_path.with_stem(input_path.stem + "_clean")

        results = process_image(
            input_path=input_path,
            output_path=output_path,
            sizes=list(sizes) if sizes else None,
            config=config,
            skip_steps=skip,
        )
        processed_path = results[0]
        click.echo(f"Processed: {processed_path}")

    click.echo("Generating Etsy listing metadata...")
    listing = generate_listing(processed_path, model=model)

    if save_json:
        json_path = save_metadata(listing, processed_path.with_suffix(".json"))
        click.echo(f"✓ Saved metadata: {json_path}")

    if json_out:
        click.echo(json_mod.dumps({
            "title": listing.title,
            "tags": listing.tags,
            "description": listing.description,
        }, indent=2))
    else:
        click.echo(f"\nTitle: {listing.title}")
        click.echo(f"\nTags: {', '.join(listing.tags)}")
        click.echo(f"\nDescription:\n{listing.description}")


@main.command("batch-listing")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-o", "--output", "output_dir", type=click.Path(path_type=Path), default=None,
              help="Output directory (default: <directory>/output).")
@click.option("-s", "--size", "sizes", multiple=True,
              help="Print size. Repeatable.")
@click.option("--dpi", default=300, show_default=True)
@click.option("--skip", "skip_steps", multiple=True,
              help="Skip processing step. Repeatable.")
@click.option("--no-perspective", is_flag=True)
@click.option("--skip-processing", is_flag=True,
              help="Skip image processing, use images directly.")
@click.option("--model", default="claude-sonnet-4-20250514", show_default=True,
              help="Claude model for listing generation.")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
def batch_listing(directory, output_dir, sizes, dpi, skip_steps,
                  no_perspective, skip_processing, model, verbose, quiet):
    """Process all images in a directory and generate Etsy listings.

    Saves processed images and JSON metadata sidecar files to the output directory.
    """
    _setup_logging(verbose, quiet)

    skip = set(skip_steps)
    if no_perspective:
        skip.add("perspective")

    config = PipelineConfig(output_dpi=dpi)
    output_dir = output_dir or directory / "output"

    images = sorted(
        p for p in directory.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith(".")
    )

    if not images:
        click.echo(f"No images found in {directory}")
        return

    click.echo(f"Processing {len(images)} images...")
    success = 0
    for img_path in images:
        try:
            if skip_processing:
                processed_path = img_path
            else:
                results = process_image(
                    input_path=img_path,
                    output_path=output_dir / (img_path.stem + "_clean.png"),
                    sizes=list(sizes) if sizes else None,
                    config=config,
                    skip_steps=skip,
                )
                processed_path = results[0]
                click.echo(f"  ✓ Processed: {processed_path}")

            listing = generate_listing(processed_path, model=model)
            json_path = save_metadata(listing, output_dir / (img_path.stem + "_listing.json"))
            click.echo(f"  ✓ Listing: {json_path} — {listing.title[:60]}")
            success += 1
        except Exception as e:
            click.echo(f"  ✗ {img_path.name}: {e}", err=True)

    click.echo(f"Done. {success}/{len(images)} listings generated.")


@main.command()
@click.option("--api-key", prompt="Etsy API Key", help="Your Etsy API key (client_id).")
@click.option("--port", default=5555, show_default=True,
              help="Local port for OAuth callback.")
@click.option("--credentials", "creds_path", type=click.Path(path_type=Path), default=None,
              help="Path to save credentials (default: ~/.etsy-assistant/credentials.json).")
@click.option("-v", "--verbose", is_flag=True)
def auth(api_key, port, creds_path, verbose):
    """Authenticate with Etsy via OAuth 2.0.

    Opens your browser to authorize the app, then saves credentials locally.
    """
    from etsy_assistant.etsy_api import authorize

    _setup_logging(verbose, False)

    click.echo("Starting Etsy OAuth flow...")
    click.echo(f"A browser window will open. Authorize the app, then return here.")

    creds = authorize(api_key, port=port)
    path = creds.save(creds_path)

    click.echo(f"✓ Authenticated as user {creds.user_id}")
    if creds.shop_id:
        click.echo(f"✓ Shop ID: {creds.shop_id}")
    click.echo(f"✓ Credentials saved to {path}")


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("-p", "--price", type=float, prompt="Listing price",
              help="Price in your shop's currency.")
@click.option("--taxonomy-id", type=int, default=None,
              help="Etsy taxonomy ID (auto-detected if omitted).")
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), default=None,
              help="Output path for processed image.")
@click.option("-s", "--size", "sizes", multiple=True,
              help="Print size. Repeatable.")
@click.option("--dpi", default=300, show_default=True)
@click.option("--skip", "skip_steps", multiple=True)
@click.option("--no-perspective", is_flag=True)
@click.option("--skip-processing", is_flag=True,
              help="Skip image processing, use input directly.")
@click.option("--model", default="claude-sonnet-4-20250514", show_default=True,
              help="Claude model for metadata generation.")
@click.option("--credentials", "creds_path", type=click.Path(path_type=Path), default=None,
              help="Path to Etsy credentials file.")
@click.option("--dry-run", is_flag=True, help="Show what would be published without creating the listing.")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
def publish(input_path, price, taxonomy_id, output_path, sizes, dpi,
            skip_steps, no_perspective, skip_processing, model, creds_path,
            dry_run, verbose, quiet):
    """Process a sketch, generate metadata, and publish as an Etsy draft listing.

    Runs the full pipeline: image cleanup -> AI metadata generation -> Etsy upload.
    Creates a DRAFT listing (not active) so you can review before going live.
    """
    from etsy_assistant.etsy_api import (
        EtsyCredentials,
        create_draft_listing,
        upload_listing_file,
        upload_listing_image,
    )

    _setup_logging(verbose, quiet)

    # Step 1: Process image
    if skip_processing:
        processed_path = input_path
    else:
        skip = set(skip_steps)
        if no_perspective:
            skip.add("perspective")

        config = PipelineConfig(output_dpi=dpi)
        if output_path is None:
            output_path = input_path.with_stem(input_path.stem + "_clean")

        results = process_image(
            input_path=input_path,
            output_path=output_path,
            sizes=list(sizes) if sizes else None,
            config=config,
            skip_steps=skip,
        )
        processed_path = results[0]
        click.echo(f"✓ Processed: {processed_path}")

    # Step 2: Generate listing metadata
    click.echo("Generating listing metadata...")
    listing_meta = generate_listing(processed_path, model=model)
    json_path = save_metadata(listing_meta, processed_path.with_suffix(".json"))
    click.echo(f"✓ Metadata saved: {json_path}")

    click.echo(f"\n  Title: {listing_meta.title}")
    click.echo(f"  Tags:  {', '.join(listing_meta.tags)}")
    click.echo(f"  Price: {price}")

    if dry_run:
        click.echo("\n[dry-run] Skipping Etsy upload.")
        return

    # Step 3: Create draft listing on Etsy
    creds = EtsyCredentials.load(creds_path)

    click.echo("\nCreating Etsy draft listing...")
    draft = create_draft_listing(
        creds=creds,
        title=listing_meta.title,
        description=listing_meta.description,
        tags=listing_meta.tags,
        price=price,
        taxonomy_id=taxonomy_id or 1,
        creds_path=creds_path,
    )
    click.echo(f"✓ Draft listing created: {draft.listing_id}")

    # Step 4: Upload preview image
    click.echo("Uploading preview image...")
    upload_listing_image(creds, draft.listing_id, processed_path, creds_path)
    click.echo(f"✓ Preview image uploaded")

    # Step 5: Upload digital download file
    click.echo("Uploading digital download file...")
    upload_listing_file(creds, draft.listing_id, processed_path, creds_path)
    click.echo(f"✓ Digital file uploaded")

    if draft.url:
        click.echo(f"\nListing URL: {draft.url}")
    click.echo(f"\nDraft listing {draft.listing_id} is ready for review on Etsy!")
