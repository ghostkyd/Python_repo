#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_payload_to_json.py — 将 gmlogger 日志中的 protobuf payload（如 parkingSpotsMap）还原为可读 JSON。

用法:
    python3 log_payload_to_json.py <日志文件路径> [--topic parkingSpotsMap] [--outdir <输出目录>]

说明:
    - 从每行日志中解析 "topic: <主题> payload: <base64>"，记录该行所在行号与日志时间。
    - 同一 payload（base64 内容相同）只解码一次（去重），但会保留出现次数、首次/末次行号与时间。
    - 输出文件命名: <日志文件名不带扩展名>_<topic>_unique.json，默认生成在与日志相同的目录，
      可用 --outdir 指定输出目录。
    - 解码使用内嵌的 proto3 schema（cls.vehicle.adas.parking.v1.ParkingSpotsMap），
      定义来源于工程: cls/vehicle/adas/parking/v1/parking_perception_topics.proto 与 parking_spot_info.proto。
      该解码逻辑已与 protoc 输出交叉验证一致。

依赖: 仅 Python 标准库（无需安装 protobuf / protoc）。
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import struct

# ============================================================================
# Part 1: 通用 protobuf wire-format 解析
# ============================================================================

def _read_varint(buf, idx):
    ln = 0
    shift = 0
    while True:
        b = buf[idx]
        idx += 1
        ln |= (b & 0x7f) << shift
        shift += 7
        if not (b & 0x80):
            return ln, idx


def parse_fields(buf):
    """把一段 protobuf 二进制解析为 [(field_number, wire_type, raw_value), ...]"""
    out = []
    idx = 0
    n = len(buf)
    while idx < n:
        tag, idx = _read_varint(buf, idx)
        field = tag >> 3
        wire = tag & 7
        if wire == 0:                       # varint
            v, idx = _read_varint(buf, idx)
            out.append((field, wire, v))
        elif wire == 1:                     # 64-bit
            out.append((field, wire, buf[idx:idx + 8]))
            idx += 8
        elif wire == 2:                     # length-delimited
            ln, idx = _read_varint(buf, idx)
            out.append((field, wire, buf[idx:idx + ln]))
            idx += ln
        elif wire == 5:                     # 32-bit
            out.append((field, wire, buf[idx:idx + 4]))
            idx += 4
        else:
            raise ValueError("unsupported wire type %d at field %d" % (wire, field))
    return out


def _f32(raw):
    return struct.unpack('<f', raw)[0]


# ============================================================================
# Part 2: ParkingSpotsMap schema（来自工程 proto 定义）
# ============================================================================
# message ParkingSpotsMap {
#   google.protobuf.Timestamp timestamp = 1;      // { seconds=1, nanos=2 }
#   repeated ParkingSpotInfo   parking_spots = 2;
# }
# message ParkingSpotInfo {
#   int32  spot_id = 1;
#   Type   type    = 2;    // 0 TYPE_UNSPECIFIED / 10 PERPENDICULAR / 11 PARALLEL / 12 SLANTED
#   State  state   = 3;    // 0..7: UNSPECIFIED/NOT_APPLICABLE/AVAILABLE/OCCUPIED/SELECTED/UNAVAILABLE/RECOMMENDED/USER_DEFINED_UNAVAILABLE
#   SpotPoint corner1..corner4 = 4,5,6,7;         // { float x=1, y=2, z=3 }
#   ParkingDirection parking_direction = 8;       // 0 PD_UNSPECIFIED / 1 PD_FRONT / 2 PD_BACK / 3 PD_DEFAULT
#   optional int32 estimated_num_legs_front_in = 9;
#   optional int32 estimated_num_legs_back_in  = 10;
#   GroundLockState ground_lock_state = 11;
#   bool  is_offset_parking_button_visible = 12;
#   OffsetParkingButtonStatus offset_to_left_parking_button_status  = 13;
#   OffsetParkingButtonStatus middle_parking_button_status          = 14;
#   OffsetParkingButtonStatus offset_to_right_parking_button_status = 15;
#   SlotProperty slot_property = 16;
#   int32 slot_display_id = 101;
#   Direction_Change_Status direction_change_status = 102;
#   Current_Direction      current_direction        = 103;
# }
# message SpotPoint { float x = 1; float y = 2; float z = 3; }
# enum ParkingDirection { PD_UNSPECIFIED=0; PD_FRONT=1; PD_BACK=2; PD_DEFAULT=3; }

TYPE_NAMES = {0: "TYPE_UNSPECIFIED", 10: "PERPENDICULAR", 11: "PARALLEL", 12: "SLANTED"}
STATE_NAMES = {0: "STATE_UNSPECIFIED", 1: "NOT_APPLICABLE", 2: "AVAILABLE", 3: "OCCUPIED",
               4: "SELECTED", 5: "UNAVAILABLE", 6: "RECOMMENDED", 7: "USER_DEFINED_UNAVAILABLE"}
DIR_NAMES = {0: "PD_UNSPECIFIED", 1: "PD_FRONT", 2: "PD_BACK", 3: "PD_DEFAULT"}
GLS_NAMES = {0: "GLS_UNSPECIFIED", 1: "GLS_NO_GROUND_LOCK", 2: "GLS_GROUND_LOCK_CLOSED", 3: "GLS_GROUND_LOCK_OPEN"}
BTN_NAMES = {0: "BUTTON_STATUS_UNSPECIFIED", 1: "BUTTON_STATUS_DISABLED", 2: "BUTTON_STATUS_ENABLED", 3: "BUTTON_STATUS_HIGHLIGHTED"}
PROP_NAMES = {0: "PROPERTY_UNSPECIFIED", 1: "PROPERTY_NORMAL", 2: "PROPERTY_MECHANICAL"}
DIRCHG_NAMES = {0: "DIRCHANGE_UNSPECIFIED", 1: "DIRCHANGE_NOT_AVAILABLE", 2: "DIRCHANGE_AVAILABLE"}
CURDIR_NAMES = {0: "DIREACTION_UNSPECIFIED", 1: "BACK_IN", 2: "HEAD_IN"}

TYPE_URL = "type.googleapis.com/cls.vehicle.adas.parking.v1.ParkingSpotsMap"


def _enum_name(mapping, v):
    return mapping.get(v, "UNKNOWN_%d" % v)


def _decode_spot_point(buf):
    d = {}
    for field, wire, raw in parse_fields(buf):
        if field == 1 and wire == 5:
            d['x'] = _f32(raw)
        elif field == 2 and wire == 5:
            d['y'] = _f32(raw)
        elif field == 3 and wire == 5:
            d['z'] = _f32(raw)
        else:
            d.setdefault('_unknown_fields', []).append(
                (field, wire, raw.hex() if isinstance(raw, bytes) else raw))
    return d


def _decode_spot_info(buf):
    d = {}
    for field, wire, raw in parse_fields(buf):
        if field == 1 and wire == 0:
            d['spot_id'] = raw
        elif field == 2 and wire == 0:
            d['type'] = _enum_name(TYPE_NAMES, raw)
        elif field == 3 and wire == 0:
            d['state'] = _enum_name(STATE_NAMES, raw)
        elif field == 4 and wire == 2:
            d['corner1'] = _decode_spot_point(raw)
        elif field == 5 and wire == 2:
            d['corner2'] = _decode_spot_point(raw)
        elif field == 6 and wire == 2:
            d['corner3'] = _decode_spot_point(raw)
        elif field == 7 and wire == 2:
            d['corner4'] = _decode_spot_point(raw)
        elif field == 8 and wire == 0:
            d['parking_direction'] = _enum_name(DIR_NAMES, raw)
        elif field == 9 and wire == 0:
            d['estimated_num_legs_front_in'] = raw
        elif field == 10 and wire == 0:
            d['estimated_num_legs_back_in'] = raw
        elif field == 11 and wire == 0:
            d['ground_lock_state'] = _enum_name(GLS_NAMES, raw)
        elif field == 12 and wire == 0:
            d['is_offset_parking_button_visible'] = bool(raw)
        elif field == 13 and wire == 0:
            d['offset_to_left_parking_button_status'] = _enum_name(BTN_NAMES, raw)
        elif field == 14 and wire == 0:
            d['middle_parking_button_status'] = _enum_name(BTN_NAMES, raw)
        elif field == 15 and wire == 0:
            d['offset_to_right_parking_button_status'] = _enum_name(BTN_NAMES, raw)
        elif field == 16 and wire == 0:
            d['slot_property'] = _enum_name(PROP_NAMES, raw)
        elif field == 101 and wire == 0:
            d['slot_display_id'] = raw
        elif field == 102 and wire == 0:
            d['direction_change_status'] = _enum_name(DIRCHG_NAMES, raw)
        elif field == 103 and wire == 0:
            d['current_direction'] = _enum_name(CURDIR_NAMES, raw)
        else:
            d.setdefault('_unknown_fields', []).append(
                (field, wire, raw.hex() if isinstance(raw, bytes) else raw))
    return d


def _decode_timestamp(buf):
    ts = {}
    for field, wire, raw in parse_fields(buf):
        if field == 1 and wire == 0:
            ts['seconds'] = raw
        elif field == 2 and wire == 0:
            ts['nanos'] = raw
    return ts


def _decode_parking_spots_map(buf):
    d = {'parking_spots': []}
    for field, wire, raw in parse_fields(buf):
        if field == 1 and wire == 2:
            d['timestamp'] = _decode_timestamp(raw)
        elif field == 2 and wire == 2:
            d['parking_spots'].append(_decode_spot_info(raw))
        else:
            d.setdefault('_unknown_fields', []).append(
                (field, wire, raw.hex() if isinstance(raw, bytes) else raw))
    return d


def _decode_any(buf):
    """google.protobuf.Any: field1=type_url(string), field2=value(bytes)"""
    type_url = None
    value = None
    for field, wire, raw in parse_fields(buf):
        if field == 1 and wire == 2:
            type_url = raw.decode(errors='replace')
        elif field == 2 and wire == 2:
            value = raw
    return type_url, value


def decode_parking_spots_payload(b64):
    """输入 base64 payload 字符串，返回可读 dict（含 timestamp、parking_spots 等）。"""
    raw = base64.b64decode(''.join(b64.split()))
    type_url, value = _decode_any(raw)
    if type_url != TYPE_URL:
        raise ValueError("unexpected type_url: %s" % type_url)
    data = _decode_parking_spots_map(value)
    ts = data.get('timestamp', {})
    secs = ts.get('seconds', 0)
    nanos = ts.get('nanos', 0)
    base = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=secs, microseconds=nanos / 1000)
    data['timestamp_iso8601'] = base.strftime('%Y-%m-%dT%H:%M:%S') + '.%09dZ' % nanos
    data['timestamp_utc'] = base.strftime('%Y-%m-%d %H:%M:%S') + ' UTC'
    return data


# ============================================================================
# Part 3: 日志解析 / 去重 / 输出
# ============================================================================

# 示例行:
# 11.log:39-main.log_2026_10_31_16_35_55:10-31 16:35:37.172  4950  4980 I KANZI_SERVICE: SensorDataResolve:setApaData topic: parkingSpotsMap payload: Cj90eX...
TOPIC_PAYLOAD_RE = re.compile(r'topic:\s*([A-Za-z0-9_]+)\s+payload:\s*(\S+)')
LOG_TIME_RE = re.compile(r'(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})')

# 已知 schema 的 topic 列表（未来可扩展）
KNOWN_TOPICS = {
    "parkingSpotsMap": decode_parking_spots_payload,
}


def parse_log_entries(log_path):
    """返回 [{'topic', 'payload', 'line', 'log_timestamp'}, ...]"""
    entries = []
    with open(log_path, errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            m = TOPIC_PAYLOAD_RE.search(line)
            if not m:
                continue
            tm = LOG_TIME_RE.search(line)
            entries.append({
                'topic': m.group(1),
                'payload': m.group(2),
                'line': lineno,
                'log_timestamp': tm.group(1) if tm else '',
            })
    return entries


def build_unique_results(entries, decoder):
    """按 payload 内容去重（保留首次/末次出现的行号与时间），返回结果列表。"""
    first = {}   # payload -> index
    metas = {}   # payload -> {'occurrences','first_line','first_ts','last_line','last_ts'}
    order = []
    for e in entries:
        p = e['payload']
        if p not in metas:
            metas[p] = {'occurrences': 0, 'first_line': e['line'],
                        'first_ts': e['log_timestamp'],
                        'last_line': e['line'], 'last_ts': e['log_timestamp']}
            order.append(p)
        m = metas[p]
        m['occurrences'] += 1
        m['last_line'] = e['line']
        m['last_ts'] = e['log_timestamp'] or m['last_ts']

    results = []
    for idx, p in enumerate(order, 1):
        m = metas[p]
        try:
            decoded = decoder(p)
            entry = {
                'index': idx,
                'payload_sha256': hashlib.sha256(p.encode()).hexdigest(),
                'occurrences': m['occurrences'],
                'first_log_line': m['first_line'],
                'first_log_timestamp': m['first_ts'],
                'last_log_line': m['last_line'],
                'last_log_timestamp': m['last_ts'],
            }
            entry.update(decoded)
        except Exception as exc:  # 解码失败时保留原始 payload，不中断整体流程
            entry = {
                'index': idx,
                'payload_sha256': hashlib.sha256(p.encode()).hexdigest(),
                'occurrences': m['occurrences'],
                'first_log_line': m['first_line'],
                'first_log_timestamp': m['first_ts'],
                'last_log_line': m['last_line'],
                'last_log_timestamp': m['last_ts'],
                'decode_error': str(exc),
                'payload': p,
            }
        results.append(entry)
    return results


def process_log(log_path, topic_filter=None, outdir=None):
    log_dir = os.path.dirname(os.path.abspath(log_path))
    base = os.path.splitext(os.path.basename(log_path))[0]
    outdir = outdir or log_dir
    os.makedirs(outdir, exist_ok=True)

    entries = parse_log_entries(log_path)
    topics = sorted({e['topic'] for e in entries})
    if topic_filter:
        topics = [t for t in topics if t == topic_filter]
        if not topics:
            raise SystemExit("未在日志中找到 topic=%s 的行" % topic_filter)

    written = []
    for topic in topics:
        decoder = KNOWN_TOPICS.get(topic)
        topic_entries = [e for e in entries if e['topic'] == topic]
        if decoder is None:
            # 未知 topic：仅去重并标记不支持解码
            results = build_unique_results(topic_entries, lambda p: (_ for _ in ()).throw(
                ValueError("unsupported topic schema: %s" % topic)))
        else:
            results = build_unique_results(topic_entries, decoder)

        doc = {
            'source_log': os.path.abspath(log_path),
            'topic': topic,
            'decode_schema': TYPE_URL if decoder else "unsupported",
            'total_payload_occurrences': len(topic_entries),
            'unique_payloads': len(results),
            'results': results,
        }
        out_path = os.path.join(outdir, '%s_%s_unique.json' % (base, topic))
        with open(out_path, 'w') as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        written.append((out_path, len(topic_entries), len(results), decoder is not None))
    return written


def main():
    ap = argparse.ArgumentParser(description='gmlogger 日志 payload → 可读 JSON（按主题去重）')
    ap.add_argument('log_path', help='gmlogger 日志文件路径，如 .../12/44.log')
    ap.add_argument('--topic', default=None, help='只处理指定 topic（默认处理日志中出现的全部 topic）')
    ap.add_argument('--outdir', default=None, help='输出目录（默认与日志同目录）')
    args = ap.parse_args()

    if not os.path.isfile(args.log_path):
        raise SystemExit("文件不存在: %s" % args.log_path)

    for out_path, total, unique, ok in process_log(args.log_path, args.topic, args.outdir):
        status = '已解码' if ok else '不支持该 schema，仅去重'
        print('输出: %s  (出现 %d 次 / 去重 %d 条, %s)' % (out_path, total, unique, status))


if __name__ == '__main__':
    main()
