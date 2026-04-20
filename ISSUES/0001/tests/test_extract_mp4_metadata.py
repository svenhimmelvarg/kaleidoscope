import sys
import os
import subprocess
import json

def test_extraction():
    os.system("ffmpeg -y -f lavfi -i color=c=black:s=16x16 -frames:v 1 -movflags use_metadata_tags -metadata elapsed_ms=1234 -metadata wait_time_ms=5678 dummy.mp4 2>/dev/null")
    
    cmd = [
        'ffprobe',
        '-v',
        'quiet',
        '-print_format',
        'json',
        '-show_format',
        'dummy.mp4',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    tags = data.get('format', {}).get('tags', {})
    
    elapsed = tags.get('elapsed_ms')
    wait_time = tags.get('wait_time_ms')
    
    print(f"elapsed_ms: {elapsed}")
    print(f"wait_time_ms: {wait_time}")
    
    if str(elapsed) == "1234" and str(wait_time) == "5678":
        print("Success!")
    else:
        print("Failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_extraction()
