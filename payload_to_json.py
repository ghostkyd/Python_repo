#!/usr/bin/env python3
"""Deduplicate and decode parkingSpotsMap payloads from one Kanzi log.

Usage:
    python3 payload_to_json.py /path/to/12/44.log

The output is one JSON array. Each unique payload is decoded once and contains
its SHA-256 fingerprint, occurrence count, first/last log positions, internal
protobuf timestamp, and parking spots.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


TYPE_URL = "type.googleapis.com/cls.vehicle.adas.parking.v1.ParkingSpotsMap"
PAYLOAD_RE = re.compile(r"\bpayload\s*[:=]\s*([A-Za-z0-9+/=_-]+)", re.I)
ISO_TIME_RE = re.compile(r"(?P<t>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)")
SHORT_TIME_RE = re.compile(r"(?P<t>\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?)")
NAMED_TIME_RE = re.compile(r"(?:log_time|timestamp|time)\s*[:=]\s*(?P<t>[^,\s\]]+)", re.I)


class DecodeError(ValueError):
    pass


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7
        if shift >= 70:
            raise DecodeError("invalid protobuf varint")
    raise DecodeError("truncated protobuf varint")


def protobuf_fields(data: bytes) -> Iterator[tuple[int, int, Any]]:
    pos = 0
    while pos < len(data):
        tag, pos = read_varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if number <= 0:
            raise DecodeError("invalid protobuf field number")
        if wire == 0:
            value, pos = read_varint(data, pos)
        elif wire == 1:
            value, pos = data[pos : pos + 8], pos + 8
        elif wire == 2:
            length, pos = read_varint(data, pos)
            value, pos = data[pos : pos + length], pos + length
        elif wire == 5:
            value, pos = data[pos : pos + 4], pos + 4
        else:
            raise DecodeError(f"unsupported protobuf wire type: {wire}")
        if pos > len(data):
            raise DecodeError("truncated protobuf field")
        yield number, wire, value


def enum(value: int, names: dict[int, str]) -> str:
    return names.get(value, f"UNKNOWN_{value}")


TYPE_NAMES = {0: "TYPE_UNSPECIFIED", 10: "PERPENDICULAR", 11: "PARALLEL", 12: "SLANTED"}
STATE_NAMES = {
    0: "STATE_UNSPECIFIED", 1: "NOT_APPLICABLE", 2: "AVAILABLE",
    3: "OCCUPIED", 4: "SELECTED", 5: "UNAVAILABLE",
    6: "RECOMMENDED", 7: "USER_DEFINED_UNAVAILABLE",
}


def decode_point(data: bytes) -> dict[str, float]:
    result: dict[str, float] = {}
    names = {1: "x", 2: "y", 3: "z"}
    for number, wire, value in protobuf_fields(data):
        if wire == 5 and number in names:
            result[names[number]] = struct.unpack("<f", value)[0]
    return result


def decode_spot(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    points = {4: "corner1", 5: "corner2", 6: "corner3", 7: "corner4"}
    for number, wire, value in protobuf_fields(data):
        if wire == 0 and number == 1:
            result["spot_id"] = value
        elif wire == 0 and number == 2:
            result["type"] = enum(value, TYPE_NAMES)
        elif wire == 0 and number == 3:
            result["state"] = enum(value, STATE_NAMES)
        elif wire == 2 and number in points:
            result[points[number]] = decode_point(value)
    return result


def decode_timestamp(data: bytes) -> dict[str, int]:
    result: dict[str, int] = {}
    for number, wire, value in protobuf_fields(data):
        if wire == 0 and number == 1:
            result["seconds"] = value
        elif wire == 0 and number == 2:
            result["nanos"] = value
    return result


def decode_map(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"timestamp": {}, "parking_spots": []}
    for number, wire, value in protobuf_fields(data):
        if wire != 2:
            continue
        if number == 1:
            result["timestamp"] = decode_timestamp(value)
        elif number == 2:
            result["parking_spots"].append(decode_spot(value))
    return result


def decode_raw_payload(text: str) -> bytes:
    text = text.strip()
    text = re.sub(r"\s+", "", text).replace("-", "+").replace("_", "/")
    text += "=" * (-len(text) % 4)
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DecodeError(f"invalid base64 payload: {exc}") from exc
    return raw


def decode_payload(raw: bytes) -> dict[str, Any]:
    outer = list(protobuf_fields(raw))
    topic_raw = next((v for n, _w, v in outer if n == 1), None)
    value = next((v for n, _w, v in outer if n == 2), None)
    if not isinstance(topic_raw, bytes) or not isinstance(value, bytes):
        raise DecodeError("payload is not a ValidPayload protobuf")
    topic = topic_raw.decode("utf-8", errors="replace")
    if topic != TYPE_URL:
        raise DecodeError(f"unsupported topic: {topic}")
    return {"topic": topic, "value": decode_map(value)}


def extract_time(line: str, fallback: Optional[str]) -> Optional[str]:
    match = ISO_TIME_RE.search(line) or SHORT_TIME_RE.search(line)
    if match:
        return match.group("t")
    match = NAMED_TIME_RE.search(line)
    return match.group("t") if match else fallback


def timestamp_iso8601(timestamp: dict[str, int]) -> Optional[str]:
    if "seconds" not in timestamp:
        return None
    seconds = timestamp["seconds"]
    nanos = timestamp.get("nanos", 0)
    whole = datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{whole}.{nanos:09d}Z"


def safe_name(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", str(value)) or "decoded"


def output_context(log_path: Path, output_root: Optional[str], time_dir: Optional[str]) -> tuple[Path, str]:
    parent = log_path.parent
    if output_root:
        root = Path(output_root).expanduser()
    elif parent.name.isdigit():
        root = parent.parent
        time_dir = time_dir or parent.name
    else:
        root = parent
    return root, time_dir or "decoded"


def output_path(root: Path, log_path: Path, time_dir: str, overwrite: bool) -> Path:
    directory = root / safe_name(time_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{log_path.stem}_parkingSpotsMap_unique.json"
    if path.exists() and not overwrite:
        index = 2
        while True:
            candidate = directory / f"{log_path.stem}_parkingSpotsMap_unique_{index}.json"
            if not candidate.exists():
                return candidate
            index += 1
    return path


def decode_log(args: argparse.Namespace) -> int:
    log_path = Path(args.log_file).expanduser()
    root, time_dir = output_context(log_path, args.output_root, args.time_dir)
    unique: dict[str, dict[str, Any]] = {}

    with log_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line_number, line in enumerate(stream, 1):
            match = PAYLOAD_RE.search(line)
            if not match:
                continue
            log_time = extract_time(line, args.log_time)
            if log_time is None:
                raise DecodeError(
                    f"{log_path}:{line_number}: cannot find log time; "
                    "use --log-time or add a supported timestamp"
                )

            # Hash the decoded protobuf bytes.  This treats equivalent Base64
            # spellings as the same payload and decodes each unique value once.
            raw = decode_raw_payload(match.group(1))
            fingerprint = hashlib.sha256(raw).hexdigest()
            current = unique.get(fingerprint)
            if current is None:
                decoded = decode_payload(raw)
                value = decoded["value"]
                current = {
                    "index": len(unique) + 1,
                    "payload_sha256": fingerprint,
                    "occurrences": 1,
                    "first_log_line": line_number,
                    "first_log_timestamp": log_time,
                    "last_log_line": line_number,
                    "last_log_timestamp": log_time,
                    "timestamp": value["timestamp"],
                    "timestamp_iso8601": timestamp_iso8601(value["timestamp"]),
                    "parking_spots": value["parking_spots"],
                }
                unique[fingerprint] = current
            else:
                current["occurrences"] += 1
                current["last_log_line"] = line_number
                current["last_log_timestamp"] = log_time

    records = list(unique.values())
    if not records:
        print("warning: no payload lines found", file=sys.stderr)
        return 0

    path = output_path(root, log_path, time_dir, args.overwrite)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    print(f"merged {sum(r['occurrences'] for r in records)} occurrences into {len(records)} unique payloads", file=sys.stderr)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_file", help="log file containing payload lines")
    parser.add_argument("--log-time", help="fallback timestamp if a line has no timestamp")
    parser.add_argument("--time-dir", help="override output subdirectory, for example 12")
    parser.add_argument("--output-root", help="override output root directory")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing merged JSON")
    args = parser.parse_args(argv)
    try:
        return decode_log(args)
    except (OSError, DecodeError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
