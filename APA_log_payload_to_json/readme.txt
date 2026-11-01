python3 log_payload_to_json.py <日志文件>                # 处理日志中全部主题
python3 log_payload_to_json.py <日志文件> --topic parkingSpotsMap   # 只处理指定主题
python3 log_payload_to_json.py <日志文件> --outdir <目录>            # 自定义输出目录

{
  "index": 244,
  "payload_sha256": "…完整 64 位指纹…",
  "occurrences": 2,                     // 在日志中出现次数
  "first_log_line": 487,                // 首次出现的日志行号
  "first_log_timestamp": "10-31 16:36:24.368",   // 首次出现日志时间
  "last_log_line": 488,                 // 末次出现的日志行号
  "last_log_timestamp": "10-31 16:36:24.368",
  "timestamp": {"seconds": 2, "nanos": 303481089},  // payload 内部时间戳
  "timestamp_iso8601": "1970-01-01T00:00:02.303481089Z",
  "parking_spots": [ …spot_id/type/state/corner1–4… ]
}