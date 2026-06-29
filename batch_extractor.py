import os
import sys
import time
import requests
import argparse

API_URL = "http://127.0.0.1:5000/api/extract"

def batch_process(directory_path, model="gemini-3.1-flash-lite", delay_seconds=10, minor_possible=False):
    if not os.path.exists(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return

    # Find all videos
    video_extensions = (".mp4", ".mov", ".m4v", ".avi", ".m4s", ".mkv")
    files = [f for f in os.listdir(directory_path) if f.lower().endswith(video_extensions)]
    
    if not files:
        print(f"No video files found in '{directory_path}'.")
        return
        
    print(f"Found {len(files)} videos to process in batch.")
    print(f"Allow Minors (Safety Abort Bypass): {minor_possible}")
    print("-" * 60)
    
    success_count = 0
    fail_count = 0
    
    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(directory_path, filename)
        print(f"[{idx}/{len(files)}] Processing: {filename}...")
        
        start_time = time.time()
        try:
            with open(filepath, 'rb') as f:
                response = requests.post(
                    API_URL,
                    files={"video": f},
                    data={
                        "model": model,
                        "dry_run": "false",
                        "minor_possible": "true" if minor_possible else "false"
                    }
                )
            
            elapsed = time.time() - start_time
            if response.status_code == 200:
                result = response.json()
                chunks = result.get("chunks", [])
                people_count = 0
                if chunks:
                    people_count = len(chunks[0].get("people", []))
                print(f"  ✓ Success ({elapsed:.1f}s) | Detected {people_count} person/people.")
                success_count += 1
            else:
                try:
                    err_msg = response.json().get("error", "Unknown error")
                except Exception:
                    err_msg = response.text
                print(f"  ✗ Failed ({elapsed:.1f}s) | Status {response.status_code}: {err_msg}")
                fail_count += 1
                
        except Exception as e:
            print(f"  ✗ Connection Error: {e}")
            fail_count += 1
            
        if idx < len(files):
            print(f"  Waiting {delay_seconds}s to avoid rate-limiting...")
            time.sleep(delay_seconds)
            print()
            
    print("-" * 60)
    print(f"Batch Processing Complete!")
    print(f"  Total: {len(files)} | Successful: {success_count} | Failed: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wovely Batch Video Attribute Extractor CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("directory_path", help="Path to the directory containing video files to extract attributes from")
    parser.add_argument("--model", default="gemini-3.1-flash-lite", help="Gemini model to run extraction on")
    parser.add_argument("--delay", type=int, default=10, help="Delay in seconds between files to avoid rate-limiting")
    parser.add_argument("--allow-minors", action="store_true", help="Set to true if footage may contain minors (otherwise the system aborts the run for safety)")
    
    args = parser.parse_args()
    
    batch_process(
        directory_path=args.directory_path,
        model=args.model,
        delay_seconds=args.delay,
        minor_possible=args.allow_minors
    )
