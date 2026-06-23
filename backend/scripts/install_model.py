import argparse
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel, CLIPImageProcessor, CLIPTokenizer

parser = argparse.ArgumentParser()
parser.add_argument("model_name")
parser.add_argument("save_path", type=Path)
args = parser.parse_args()

print(f"Downloading {args.model_name} to {args.save_path}")

model = CLIPModel.from_pretrained(args.model_name)
model.save_pretrained(args.save_path)

tokenizer = CLIPTokenizer.from_pretrained(args.model_name)
image_processor = CLIPImageProcessor.from_pretrained(args.model_name)

processor = CLIPProcessor(image_processor=image_processor, tokenizer=tokenizer)
processor.save_pretrained(args.save_path)

print("Done.")
