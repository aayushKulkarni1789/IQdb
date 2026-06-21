import argparse
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel

parser = argparse.ArgumentParser()
parser.add_argument("model_name")
parser.add_argument("save_path", type=Path)
args = parser.parse_args()

print(f"Downloading {args.model_name} to {args.save_path}")

model = CLIPModel.from_pretrained(f"{args.model_name}")
processor = CLIPProcessor.from_pretrained(f"{args.model_name}")

model.save_pretrained(args.save_path)
processor.save_pretrained(args.save_path)

print("Done.")
