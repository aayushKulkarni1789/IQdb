# Image Query Database (imgdb)

A local image search system that uses CLIP embeddings and ChromaDB to enable text-to-image retrieval.

## Features

- Index images using CLIP (Contrastive Language-Image Pretraining) embeddings
- Store embeddings in a local ChromaDB vector database
- Search images using natural language text prompts
- Retrieve top-k most similar images with similarity scores
- Output ranked images with similarity scores embedded in filenames
- Support for common image formats: JPG, JPEG, PNG, BMP, TIFF, GIF
- Built with UV for fast, reliable Python package management

## Installation

1. Clone or download this repository
2. Navigate to the project directory:
   ```bash
   cd /path/to/imgdb
   ```
3. Install dependencies using UV:
   ```bash
   uv sync
   ```
   (This will create a virtual environment and install all required packages)

## Usage

### Step 1: Index Your Photos

First, create a `photos/` directory and add your image files to it. Then run the indexer:

```bash
uv run python index_photos.py
```

This will:
- Scan the `photos/` directory recursively for image files
- Generate CLIP embeddings for each image
- Store the embeddings in a local ChromaDB database (`./imgdb_chroma/`)
- Show progress with a progress bar

The indexing process only needs to be run once (or when you add new photos).

### Step 2: Search for Images

Once your photos are indexed, you can search them using text prompts:

```bash
uv run python query_images.py --prompt "your search text here" --k 10 --output ./results
```

#### Arguments:
- `--prompt`: The text description to search for (required)
- `--k`: Number of top results to return (default: 5)
- `--output`: Directory where results will be saved (default: ./output)
- `--photos-dir`: Directory containing original photos (default: photos)
- `--db-path`: Path to ChromaDB database (default: ./imgdb_chroma)
- `--collection-name`: ChromaDB collection name (default: image_embeddings)
- `--model-name`: CLIP model name (default: sentence-transformers/clip-ViT-B-32)

#### Example:
```bash
uv run python query_images.py --prompt "a beautiful sunset over mountains" --k 5 --output ./sunset_results
```

### Output Format

Result files are saved in the output directory with this naming convention:
```
{rank}_{original_filename_without_ext}_{cosine_score_x1000}{extension}
```

Where:
- `{rank}`: Position in results (1, 2, 3, ...)
- `{original_filename_without_ext}`: Original filename without extension
- `{cosine_score_x1000}`: Similarity score multiplied by 1000 and converted to integer
- `{extension}`: Original file extension

#### Examples:
- `1_sunset_beach_924.jpg` = Rank 1, 92.4% similarity
- `2_mountain_view_789.png` = Rank 2, 78.9% similarity  
- `3_flower_closeup_652.bmp` = Rank 3, 65.2% similarity

## How It Works

1. **Indexing**: The `index_photos.py` script uses the sentence-transformers/clip-ViT-B-32 model to convert each image into a 512-dimensional embedding vector, which is stored in ChromaDB.

2. **Searching**: The `query_images.py` script converts your text prompt into the same embedding space, then uses ChromaDB's vector similarity search (with cosine distance) to find the most similar image embeddings.

3. **Similarity Calculation**: ChromaDB returns cosine distances, which we convert to similarity scores: `similarity = 1 - distance`. This score is then scaled to an integer (0-1000) for inclusion in output filenames.

## Technical Details

- **CLIP Model**: sentence-transformers/clip-ViT-B-32 (512-dimensional embeddings)
- **Vector Database**: ChromaDB with HNSW indexing and cosine similarity
- **Package Manager**: UV (Astral's Rust-based Python package manager)
- **Dependencies**: sentence-transformers, chromadb, pillow, tqdm, numpy
- **Persistence**: ChromaDB data stored in ./imgdb_chroma/ directory

## Notes

- The first run will download the CLIP model (~200-300MB)
- Indexing speed depends on number of images and hardware specs
- To rebuild the index from scratch, delete the ./imgdb_chroma/ directory
- The system works entirely offline after initial model download
- Similarity scores are approximate measures of semantic match quality