# Wave 4 Remote Record

- Kind: rollback-rehearsal
- Status: success
- Generated at: 2026-04-11T07:30:35Z
- Log source: /var/log/ielts-vocab/wave4/rollback-rehearsal-20260411T072946Z.log
- Log SHA256: bb6c9313e04988ae8e01c31c42af5ab1fb71271a1f03fe6ec6e5320b12afc91a
- Log lines: 64
- Exit code: 0
- Host: 119.29.182.134
- First log timestamp: 2026-04-11T07:29:46Z
- Last log timestamp: 2026-04-11T07:30:06Z

## Runtime Context

- Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- Target release: /opt/ielts-vocab/releases/20260411T033543Z-ae6204d60a3c
- Restore release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- Execute mode: true
- Storage drill after restore: false

## Command

```bash
sudo APP_HOME=/opt/ielts-vocab REHEARSAL_EXECUTE=true REHEARSAL_RUN_STORAGE_DRILL=false REHEARSAL_RECORD_PATH=/var/log/ielts-vocab/wave4/rollback-rehearsal-20260411T072946Z.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-rollback-rehearsal.sh
```

## Notes

- Storage drill evidence was captured separately in storage-drill-20260411T072543Z.log.

## Key Events

- [2026-04-11T07:29:46Z] Recording Wave 4 rollback rehearsal output to /var/log/ielts-vocab/wave4/rollback-rehearsal-20260411T072946Z.log
- [2026-04-11T07:29:46Z] Wave 4 rollback rehearsal
- [2026-04-11T07:29:46Z] Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- [2026-04-11T07:29:46Z] Target release: /opt/ielts-vocab/releases/20260411T033543Z-ae6204d60a3c
- [2026-04-11T07:29:46Z] Restore release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- [2026-04-11T07:29:46Z] Execute mode: true
- [2026-04-11T07:29:46Z] Storage drill after restore: false
- [2026-04-11T07:29:46Z] Executing rollback rehearsal to /opt/ielts-vocab/releases/20260411T033543Z-ae6204d60a3c
- [2026-04-11T07:29:56Z] Rollback completed successfully
- [2026-04-11T07:30:06Z] Rollback completed successfully
- [2026-04-11T07:30:06Z] Wave 4 rollback rehearsal completed successfully
