#!/usr/bin/env python3
# extract_logs_around_time.py
# 用法: python3 extract_logs_around_time.py /path/to/log.txt
# 默认以 "19:30:00" 为中心, 前后 10 秒 window；上下文行数为 50（关键词匹配时）
import sys, os, re
from datetime import datetime, timedelta

if len(sys.argv) < 2:
    print("Usage: python3 extract_logs_around_time.py /path/to/log.txt [center_time] [seconds_window] [context_lines]")
    print("Example center_time format: '2025-10-22 19:30:18.000' or '10-22 19:30:18.000' (script will try to detect)")
    sys.exit(1)

logpath = sys.argv[1]
center_time_arg = sys.argv[2] if len(sys.argv) >= 3 else None
sec_window = int(sys.argv[3]) if len(sys.argv) >= 4 else 10
ctx_lines = int(sys.argv[4]) if len(sys.argv) >= 5 else 50

# Keywords to capture whole-file contexts for (可根据需要增删)
KEYWORDS = [
    "requestDeactivation", "DeleteConnection", "Disconnect", "UPDATEDEACTIVATE", 
    "audiohalservice", "ASCConnectionManager", "BufferQueue", "SurfaceFlinger",
    "HWComposer", "hwc", "codec", "avcD_", "QC2Comp", "Failed to obtain result",
    "BpTransactionCompletedListener", "binder", "ANR", "timestamp", "white", "blank",
    "Blank", "render", "underrun", "underrun", "fps", "mem-usage", "DequeueBuffer",
    "QueueBuffer", "frame", "rendering", "drm", "gralloc", "vcompositor", "hwhwc"
]

# regex to extract date/time at line start like "10-22 19:30:18.000" or "2025-10-22T11:30:17.995Z"
ts_patterns = [
    re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'),   # "10-22 19:30:18.000"
    re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'), # "2025-10-22 19:30:18.000"
    re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)') # ISO
]

# derive center time
def parse_center_time(s):
    if s is None:
        # default: find first occurrence of "19:30:" in file and use that line's date if possible
        return None
    for p in ts_patterns:
        m = p.search(s)
        if m:
            tstr = m.group(1)
            # try multiple formats:
            for fmt in ("%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    dt = datetime.strptime(tstr, fmt)
                    # if month-day format, add current year as fallback
                    if fmt == "%m-%d %H:%M:%S.%f":
                        dt = dt.replace(year=datetime.now().year)
                    return dt
                except:
                    pass
    return None

# helper to parse a timestamp prefix from a log line to datetime (best-effort)
def parse_ts_from_line(line):
    for p in ts_patterns:
        m = p.search(line)
        if m:
            tstr = m.group(1)
            for fmt in ("%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ"):
                try:
                    dt = datetime.strptime(tstr, fmt)
                    if fmt == "%m-%d %H:%M:%S.%f":
                        dt = dt.replace(year=datetime.now().year)
                    return dt
                except:
                    pass
    return None

# Step 1: If center_time_arg provided, try parse it directly
center_dt = None
if center_time_arg:
    # allow input like "19:30:18" or "10-22 19:30:18.000" or full iso
    # try to parse directly
    for fmt in ("%H:%M:%S", "%H:%M:%S.%f", "%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            tmp = datetime.strptime(center_time_arg, fmt)
            if fmt == "%H:%M:%S" or fmt == "%H:%M:%S.%f":
                # attach today's date
                today = datetime.now()
                center_dt = tmp.replace(year=today.year, month=today.month, day=today.day)
            else:
                center_dt = tmp
            break
        except:
            pass

# If still None, we'll scan file for first line containing "19:30:" and use its line timestamp
if center_dt is None:
    print("No explicit center time parsed. Will auto-detect first occurrence of '19:30' in file to choose the center time.")
    with open(logpath, "r", errors="ignore") as f:
        for line in f:
            if "19:30:" in line:
                dt = parse_ts_from_line(line)
                if dt:
                    center_dt = dt
                else:
                    # fallback: use today's date + time fragment
                    try:
                        tfrag = re.search(r'19:30:\d{2}\.\d{3}', line).group(0)
                        dt = datetime.strptime(tfrag, "%H:%M:%S.%f")
                        today = datetime.now()
                        center_dt = dt.replace(year=today.year, month=today.month, day=today.day)
                    except:
                        pass
                break

if center_dt is None:
    print("ERROR: 无法确定中心时间，请传入显式的时间参数（举例: '10-22 19:30:18.000'）。")
    sys.exit(2)

start_dt = center_dt - timedelta(seconds=sec_window)
end_dt   = center_dt + timedelta(seconds=sec_window)
print(f"Using center time: {center_dt} ; extracting window: {start_dt} -> {end_dt}")

# Prepare outputs
out_window = "window_snippet.txt"
out_keywords = "keyword_snippets.txt"

# First pass: stream and write lines inside window
with open(logpath, "r", errors="ignore") as inf, \
     open(out_window, "w", errors="ignore") as outf:
    for line in inf:
        dt = parse_ts_from_line(line)
        if dt:
            if start_dt <= dt <= end_dt:
                outf.write(line)

print(f"Wrote time-window slice to {out_window}")

# Second pass: find keywords and write contexts
# We'll collect line offsets and then dump contexts
# Second pass: streaming keyword extraction with limited total size
import io
MAX_HITS = 2000       # 限制最多记录多少个命中上下文（可调小）
ctx_lines = 30         # 每个命中前后上下文行数
hits_found = 0

with open(logpath, "r", errors="ignore") as inf, \
     open(out_keywords, "w", errors="ignore") as outf:
    buffer = []
    pos = 0
    from collections import deque
    prevbuf = deque(maxlen=ctx_lines)

    for line in inf:
        lower = line.lower()
        if any(kw.lower() in lower for kw in KEYWORDS):
            hits_found += 1
            outf.write("="*80 + f"\nHit #{hits_found} at line {pos}\n")
            outf.writelines(prevbuf)
            outf.write(line)
            # write next few lines directly from stream
            for _ in range(ctx_lines):
                nxt = inf.readline()
                if not nxt:
                    break
                outf.write(nxt)
                pos += 1
            outf.write("\n\n")
            if hits_found >= MAX_HITS:
                outf.write(f"...Stopped after {MAX_HITS} hits to keep file small...\n")
                break
        prevbuf.append(line)
        pos += 1

print(f"Wrote {hits_found} keyword hits (each ±{ctx_lines} lines) to {out_keywords}")

