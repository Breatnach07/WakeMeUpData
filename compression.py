import gzip
import os
import shutil
import pandas as pd

def compress_file(input_filepath):
    """Compresses a file using Gzip level 9."""
    output_filepath = f"{input_filepath}.gz"
    
    print(f"[+] Compressing {input_filepath}...")
    orig_size = os.path.getsize(input_filepath) / (1024 * 1024)

    with open(input_filepath, 'rb') as f_in:
        with gzip.open(output_filepath, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)

    compressed_size = os.path.getsize(output_filepath) / (1024 * 1024)
    reduction = (1 - (compressed_size / orig_size)) * 100

    print(f" -> Original Size:   {orig_size:.2f} MB")
    print(f" -> Compressed Size: {compressed_size:.2f} MB ({reduction:.1f}% reduction)")
    print(f" -> Saved to: {output_filepath}\n")

if __name__ == "__main__":
    # Example paths
    files_to_compress = [
        "IT\\IT.csv",
        "databases\\transit_IT.db"
    ]

    for file_path in files_to_compress:
        if os.path.exists(file_path):
            compress_file(file_path)
        else:
            print(f"[!] File not found: {file_path}")