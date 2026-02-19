# 07-06 SUMMARY: Performance Archive

**Phase:** 07-media-archive
**Plan:** 06
**Status:** Complete
**Completed:** 2026-02-19

---

## What Was Built

### PerformanceManager (`core/archive/performance.py`)
Manages live performances and takes:

- `create_performance(work_id, date, ...)` - Create new performance
- `get_performance(performance_id)` - Retrieve performance by ID
- `list_performances(work_id)` - List all performances for a work
- `add_audio(performance_id, file_path)` - Copy audio recording
- `add_video(performance_id, file_path)` - Copy video recording
- `delete_performance(performance_id)` - Delete performance and files

### Directory Structure After Performance
```
archive/works/{work_id}/
├── metadata.json
├── realizations/
├── performances/
│   └── perf_abc456/
│       ├── metadata.json
│       ├── audio/
│       │   └── live_2026-02-19.wav
│       └── video/
│           └── live_2026-02-19.mp4
└── assets/
```

### `gsd archive perform` CLI Command
**Usage:**
```bash
gsd archive perform {work_id} --date 2026-02-19 \
  --venue "The Troubadour" --city "Los Angeles" \
  --personnel "John Doe" --personnel "Jane Smith"
```

**Options:**
- `--date` / `-d` - Performance date (YYYY-MM-DD) (required)
- `--venue` / `-v` - Venue name
- `--city` / `-c` - City
- `--personnel` / `-p` - Personnel (repeatable)
- `--position` - Setlist position
- `--notes` / `-n` - Additional notes

### File Type Support
- **Audio:** `.wav`, `.flac`, `.mp3`, `.aiff`, `.ogg`, `.m4a`
- **Video:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

---

## Verification Results

- [x] PerformanceManager.create_performance creates performance directory
- [x] PerformanceManager creates audio/ and video/ subdirectories
- [x] CLI `gsd archive perform` requires --date
- [x] Performance metadata includes venue, city, personnel
- [x] Parent work's performances list updated

---

## Files Created/Modified

| File | Changes |
|------|---------|
| `core/archive/performance.py` | PerformanceManager class |
| `apps/cli/cli.py` | cmd_archive_perform + subparser |

---

## Next Steps

- **07-07**: `gsd archive status` command + verification (checkpoint)
