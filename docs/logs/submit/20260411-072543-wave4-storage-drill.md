# Wave 4 Remote Record

- Kind: storage-drill
- Status: success
- Generated at: 2026-04-11T07:30:35Z
- Log source: /var/log/ielts-vocab/wave4/storage-drill-20260411T072543Z.log
- Log SHA256: d32fc4db2a6ec4aca81659a04b7c5ac10cd4913d338a28856effb860ef50cd34
- Log lines: 113
- Exit code: 0
- Host: 119.29.182.134
- First log timestamp: 2026-04-11T07:25:43Z
- Last log timestamp: 2026-04-11T07:26:58Z

## Runtime Context

- Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635

## Command

```bash
sudo APP_HOME=/opt/ielts-vocab SMOKE_HOST=axiomaticworld.com DRILL_RUN_REPAIR=true DRILL_EXAMPLE_AUDIO_BOOK_ID=ielts_reading_premium DRILL_EXAMPLE_AUDIO_LIMIT=200 DRILL_WORD_AUDIO_BOOK_ID=ielts_reading_premium DRILL_WORD_AUDIO_LIMIT=200 DRILL_RECORD_PATH=/var/log/ielts-vocab/wave4/storage-drill-20260411T072543Z.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh
```

## Notes

- Example-audio validation now treats lazy-generation gaps as informational by default; word-audio and example-audio were sampled with limit=200 for this operator drill.

## Key Events

- [2026-04-11T07:25:43Z] Recording Wave 4 storage drill output to /var/log/ielts-vocab/wave4/storage-drill-20260411T072543Z.log
- [2026-04-11T07:25:43Z] Wave 4 remote storage drill starting
- [2026-04-11T07:25:43Z] Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- [2026-04-11T07:26:58Z] Wave 4 remote storage drill completed
