#!/usr/bin/env python3
"""
Query the image database with a text prompt and retrieve top-k matching images.
"""

import argparse
import os
import shutil
import signal
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nQuery interrupted by user. Exiting...")
    sys.exit(0)


def main():
    # Set up signal handler for graceful interruption
    signal.signal(signal.SIGINT, signal_handler)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Search images using text prompts")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt to search for")
    parser.add_argument(
        "--k", type=int, default=5, help="Number of top results to return (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Output directory for results (default: ./output)",
    )
    parser.add_argument(
        "--photos-dir",
        type=str,
        default="photos",
        help="Directory containing original photos (default: photos)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="./imgdb_chroma",
        help="Path to ChromaDB database (default: ./imgdb_chroma)",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="image_embeddings",
        help="ChromaDB collection name (default: image_embeddings)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="sentence-transformers/clip-ViT-B-32",
        help="CLIP model name (default: sentence-transformers/clip-ViT-B-32)",
    )

    args = parser.parse_args()

    # Validate parameters
    if args.k <= 0:
        print("Error: --k must be a positive integer")
        sys.exit(1)

    if not os.path.exists(args.photos_dir):
        print(f"Error: Photos directory '{args.photos_dir}' not found.")
        sys.exit(1)

    if not os.path.exists(args.db_path):
        print(f"Error: ChromaDB database not found at '{args.db_path}'.")
        print("Please run index_photos.py first to create the database.")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Initialize ChromaDB client
    print(f"Connecting to ChromaDB at {args.db_path}...")
    try:
        client = chromadb.PersistentClient(path=args.db_path)
        collection = client.get_collection(name=args.collection_name)
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")
        sys.exit(1)

    # Load CLIP model
    print(f"Loading CLIP model '{args.model_name}'...")
    try:
        model = SentenceTransformer(args.model_name)
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        sys.exit(1)

    # Generate embedding for the text prompt
    print(f"Encoding prompt: '{args.prompt}'")
    try:
        prompt_embedding = model.encode([args.prompt], convert_to_numpy=True)
    except Exception as e:
        print(f"Error encoding prompt: {e}")
        sys.exit(1)

    # Query the database
    print(f"Searching for top {args.k} matches...")
    try:
        results = collection.query(
            query_embeddings=prompt_embedding.tolist(),
            n_results=args.k,
            include=["metadatas", "distances"],  # We need distances to calculate similarity
        )
    except Exception as e:
        print(f"Error querying database: {e}")
        sys.exit(1)

    # Process results
    if not results["ids"][0]:
        print("No matching images found.")
        return

    print(f"\nFound {len(results['ids'][0])} matching images:")
    print("-" * 60)

    copied_count = 0
    for i, (id_, distance, metadata) in enumerate(
        zip(results["ids"][0], results["distances"][0], results["metadatas"][0])
    ):
        rank = i + 1
        # Convert distance to similarity: similarity = 1 - distance (for cosine space)
        similarity = 1 - distance
        # Scale to integer for filename: 0-1000 range
        cosine_int = int(similarity * 1000)

        # Extract filename components
        original_path = metadata["full_path"]
        original_name = Path(original_path).name
        name_without_ext = Path(original_path).stem
        ext = Path(original_path).suffix

        # Create new filename with rank and cosine similarity score
        new_filename = f"{rank}_{name_without_ext}_{cosine_int}{ext}"
        output_path = os.path.join(args.output, new_filename)

        try:
            # Copy file to output directory
            shutil.copy2(original_path, output_path)

            # Print result info
            print(f"{rank:2d}. {original_name}")
            print(f"    Similarity: {similarity:.4f} ({cosine_int}/1000)")
            print(f"    Saved as: {new_filename}")
            print()

            copied_count += 1

        except Exception as e:
            print(f"Error copying {original_name}: {e}")

    print(f"Successfully copied {copied_count} images to '{args.output}'")
    print("Filename format: {rank}_{original_name_without_ext}_{cosine_score_x1000}{extension}")
    print("Example: 1_sunset_beach_924.jpg means rank 1, 92.4% similarity")


if __name__ == "__main__":
    main()
