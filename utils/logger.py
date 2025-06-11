import time
from datetime import datetime

def log_tool_call(tool_name: str, args: dict, latency: float, outcome: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- TOOL CALL LOG ---")
    print(f"Timestamp: {timestamp}")
    print(f"Tool Name: {tool_name}")
    print(f"Arguments: {args}")
    print(f"Latency: {latency:.4f} seconds")
    print(f"Outcome: {outcome}")
    print(f"---------------------\n")

def print_streaming_response(chunk: str):
    print(chunk, end="", flush=True)