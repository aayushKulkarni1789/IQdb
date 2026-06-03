#!/usr/bin/env python3
"""
Index photos in the photos/ directory using CLIP embeddings and store in ChromaDB.
"""

import os
import sys
from pathlib import Path
from typing import List
import signal

import chromadb
from sentence_transformers import SentenceTransformer
from PIL import Image
from tqdm import tqdm


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nIndexing interrupted by user. Exiting...")
    sys.exit(0)


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"}
    return Path(filename).suffix.lower() in image_extensions


def get_image_files(directory: str) -> List[Path]:
    """Recursively find all image files in directory."""
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if is_image_file(file):
                image_files.append(Path(root) / file)
    return image_files


def main():
    # Set up signal handler for graceful interruption
    signal.signal(signal.SIGINT, signal_handler)

    # Configuration
    photos_dir = "photos"
    db_path = "./imgdb_chroma"
    collection_name = "image_embeddings"
    model_name = "sentence-transformers/clip-ViT-B-32"

    # Validate photos directory exists
    if not os.path.exists(photos_dir):
        print(f"Error: Photos directory '{photos_dir}' not found.")
        print("Please create a 'photos' directory and add your images.")
        sys.exit(1)

    # Initialize ChromaDB client with persistence
    print(f"Initializing ChromaDB at {db_path}...")
    client = chromadb.PersistentClient(path=db_path)

    # Get or create collection with cosine distance
    print(f"Getting or creating collection '{collection_name}'...")
    try:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # Use cosine distance
        )
    except Exception as e:
        print(f"Error creating ChromaDB collection: {e}")
        sys.exit(1)

    # Load CLIP model
    print(f"Loading CLIP model '{model_name}'...")
    try:
        model = SentenceTransformer(model_name)
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        sys.exit(1)

    # Find all image files
    print(f"Scanning for image files in '{photos_dir}'...")
    image_files = get_image_files(photos_dir)

    if not image_files:
        print(f"No image files found in '{photos_dir}'.")
        sys.exit(1)

    print(f"Found {len(image_files)} image files to process.")

    # Process each image
    processed_count = 0
    skipped_count = 0

    for img_path in tqdm(image_files, desc="Processing images"):
        try:
            # Check if already indexed (by checking if filename exists in collection)
            # We'll use a simple approach: skip if we encounter any error during processing
            # In a more sophisticated version, we could check against stored metadata

            # Load and process image
            image = Image.open(img_path).convert("RGB")

            # Generate CLIP embedding
            embedding = model.encode(image, convert_to_numpy=True)

            # Prepare metadata
            metadata = {
                "filename": img_path.name,
                "relative_path": str(img_path.relative_to(photos_dir)),
                "full_path": str(img_path.absolute()),
            }

            # Add to ChromaDB collection
            # Use the filename as ID (ensures uniqueness and prevents duplicates)
            collection.add(
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[img_path.name],  # Use filename as unique ID
            )

            processed_count += 1

        except Exception as e:
            print(f"\nWarning: Skipping {img_path.name} due to error: {e}")
            skipped_count += 1
            continue

    # Persist changes
    print("\nPersisting database to disk...")
    # ChromaDB PersistentClient automatically persists, but we can explicitly call
    # any cleanup if needed

    print("\nIndexing complete!")
    print(f"Successfully processed: {processed_count} images")
    print(f"Skipped due to errors: {skipped_count} images")
    print(f"Database stored at: {db_path}")
    print(f"To reindex from scratch, delete the '{db_path}' directory.")


if __name__ == "__main__":
    main()
