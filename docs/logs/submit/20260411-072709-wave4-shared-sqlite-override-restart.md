# Wave 4 Remote Record

- Kind: shared-sqlite-override-restart
- Status: success
- Generated at: 2026-04-11T07:30:35Z
- Log source: /var/log/ielts-vocab/wave4/shared-sqlite-override-20260411T072709Z.log
- Log SHA256: ba442a7667da29cd0e54ba93b557c055308ee9dcb96ab4c559983c1eb747bf18
- Log lines: 12
- Exit code: 0
- Host: 119.29.182.134
- First log timestamp: 2026-04-11T07:27:09Z
- Last log timestamp: 2026-04-11T07:27:10Z

## Runtime Context

- Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- Target services: notes-service
- Ready timeout seconds: 45

## Command

```bash
sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-20260411T072709Z.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service
```

## Key Events

- [2026-04-11T07:27:09Z] Recording Wave 4 shared SQLite override restart output to /var/log/ielts-vocab/wave4/shared-sqlite-override-20260411T072709Z.log
- [2026-04-11T07:27:09Z] Wave 4 shared SQLite override restart
- [2026-04-11T07:27:09Z] Current release: /opt/ielts-vocab/releases/20260411T034236Z-c4e47b654635
- [2026-04-11T07:27:09Z] Target services: notes-service
- [2026-04-11T07:27:09Z] Ready timeout seconds: 45
- [2026-04-11T07:27:09Z] Applying scoped shared SQLite override for: notes-service
- [2026-04-11T07:27:09Z] Restarting ielts-service@notes-service
- [2026-04-11T07:27:09Z] Waiting for ready URL: http://127.0.0.1:8107/ready
- [2026-04-11T07:27:10Z] Ready URL responded: http://127.0.0.1:8107/ready
- [2026-04-11T07:27:10Z] Wave 4 shared SQLite override restart completed for: notes-service
