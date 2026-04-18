#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parent
for extra_path in (
    REPO_ROOT / 'packages' / 'platform-sdk',
    REPO_ROOT / 'services' / 'tts-media-service',
):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from dotenv import load_dotenv

from services.word_tts_full_batch_task import (
    build_package_upload_payload,
    build_manifest,
    cleanup_word_audio_cache,
    json_dump,
    load_or_create_manifest,
    load_or_create_progress,
    resolve_task_files,
    resolve_upload_payload_path,
    update_progress,
    verify_manifest_cache,
)

load_dotenv(BACKEND_ROOT / '.env')
DEFAULT_OSS_PREFIX = 'projects/ielts-vocab/word-tts-cache'
SEGMENTED_OSS_PREFIX = f'{DEFAULT_OSS_PREFIX}/segmented'
SEGMENTED_WORD_CACHE_TAG = 'azure-word-segmented-v1'


def _provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


def _require_provider_credentials(provider: str) -> bool:
    if provider == 'azure':
        if not os.environ.get('AZURE_SPEECH_KEY', '').strip():
            print('ERROR: 请在 backend/.env 中设置 AZURE_SPEECH_KEY', file=sys.stderr)
            return False
        if not os.environ.get('AZURE_SPEECH_REGION', '').strip():
            print('ERROR: 请在 backend/.env 中设置 AZURE_SPEECH_REGION', file=sys.stderr)
            return False
        return True
    if provider != 'minimax' and not os.environ.get('DASHSCOPE_API_KEY', '').strip():
        print('ERROR: 请在 backend/.env 中设置 DASHSCOPE_API_KEY', file=sys.stderr)
        return False
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='词书单词 TTS 全量分包生成')
    parser.add_argument(
        '--mode',
        choices=('word', 'word-segmented'),
        default='word',
        help='生成模式：普通单词音频或按音标分段的单词音频',
    )
    parser.add_argument('--jobs', '-j', type=int, default=None, help='并发线程数')
    parser.add_argument('--book', action='append', default=[], help='仅跑指定词书 id')
    parser.add_argument('--rate-interval', type=float, default=None, help='相邻 API 请求最小间隔秒数')
    parser.add_argument('--package-size', type=int, default=1000, help='任务包大小，默认 1000')
    parser.add_argument('--start-package', type=int, default=None, help='从指定任务包索引开始')
    parser.add_argument('--reset-task', action='store_true', help='清理当前任务相关旧音频并从头开始跑')
    parser.add_argument('--stop-after-packages', type=int, default=None, help='最多连续处理多少个任务包')
    parser.add_argument('--upload-oss', action='store_true', help='每个任务包完成后上传到 OSS')
    parser.add_argument('--oss-prefix', default=None, help='OSS 对象前缀')
    parser.add_argument(
        '--axi-app-cli-root',
        default=str((BACKEND_ROOT.parent.parent / 'axi-app-cli').resolve()),
        help='axi-app-cli 根目录，用于复用 ali-oss 依赖',
    )
    return parser


def _package_progress_update(
    progress_path: Path,
    progress: dict,
    *,
    status: str,
    next_package_index: int,
    current_package_index: int | None,
    current_package_completed: int,
    current_package_total: int,
    completed_words: int,
    current_word: str | None,
    completed_package_indices: list[int] | None = None,
) -> dict:
    updates = {
        'status': status,
        'next_package_index': next_package_index,
        'current_package_index': current_package_index,
        'current_package_completed': current_package_completed,
        'current_package_total': current_package_total,
        'completed_words': completed_words,
        'current_word': current_word,
    }
    if completed_package_indices is not None:
        updates['completed_package_indices'] = completed_package_indices
    return update_progress(progress_path, progress, **updates)


def _upload_package_to_oss(
    *,
    cache_dir: Path,
    package: dict,
    package_words: list[str],
    cache_model: str,
    voice: str,
    normalize_word_key,
    word_tts_cache_path,
    oss_prefix: str,
    axi_app_cli_root: Path,
    upload_concurrency: int,
    task_name: str | None = None,
) -> dict:
    payload = build_package_upload_payload(
        package,
        package_words,
        cache_dir=cache_dir,
        model=cache_model,
        voice=voice,
        normalize_word_key=normalize_word_key,
        word_tts_cache_path=word_tts_cache_path,
        oss_prefix=oss_prefix,
    )
    payload_path = resolve_upload_payload_path(
        cache_dir,
        int(package['index']),
        task_name=task_name,
    )
    json_dump(payload_path, payload)

    command = [
        'node',
        str(BACKEND_ROOT / 'scripts' / 'upload_word_tts_package_to_oss.mjs'),
        '--payload',
        str(payload_path),
        '--env-file',
        str(BACKEND_ROOT / '.env'),
        '--axi-root',
        str(axi_app_cli_root),
        '--concurrency',
        str(max(1, int(upload_concurrency))),
    ]
    completed = subprocess.run(
        command,
        cwd=BACKEND_ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stderr.strip():
        print(completed.stderr.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip() or completed.stdout.strip() or 'OSS upload failed'
        )
    stdout = completed.stdout.strip()
    if not stdout:
        raise RuntimeError('OSS upload returned no summary')
    try:
        return json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'OSS upload returned invalid JSON: {stdout}') from exc


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    batch_mode = args.mode
    provider = 'azure' if batch_mode == 'word-segmented' else _provider()
    if not _require_provider_credentials(provider):
        return 1

    from services.word_tts import (
        _strip_word_tts_strategy_tag,
        azure_default_model,
        azure_word_voice,
        collect_unique_words,
        count_cached_words,
        default_word_tts_identity,
        is_probably_valid_mp3_file,
        lookup_azure_word_phonetic,
        normalize_word_key,
        recommended_batch_backoff_delays,
        recommended_batch_concurrency,
        recommended_batch_rate_interval,
        run_batch_generate_words,
        word_tts_cache_path,
        word_tts_data_dir,
    )

    cache_dir = word_tts_data_dir()
    task_name = 'word_tts_segmented_batch' if batch_mode == 'word-segmented' else None
    manifest_path, progress_path, verification_path = resolve_task_files(cache_dir, task_name=task_name)
    if batch_mode == 'word-segmented':
        request_model = azure_default_model()
        cache_model = f'{request_model}@{SEGMENTED_WORD_CACHE_TAG}'
        voice = azure_word_voice()
        content_mode = 'word-segmented'
        phonetic_lookup = lookup_azure_word_phonetic
    else:
        _, cache_model, voice = default_word_tts_identity()
        request_model = _strip_word_tts_strategy_tag(cache_model)
        content_mode = 'word'
        phonetic_lookup = None
    package_size = max(1, int(args.package_size))
    book_ids = args.book or None
    words = collect_unique_words(book_ids)
    rate_interval = (
        args.rate_interval
        if args.rate_interval is not None
        else recommended_batch_rate_interval(request_model, provider=provider)
    )
    jobs = max(
        1,
        int(
            args.jobs
            if args.jobs is not None
            else recommended_batch_concurrency(request_model, provider=provider)
        ),
    )
    backoff = recommended_batch_backoff_delays(rate_interval)
    oss_prefix = args.oss_prefix or (
        SEGMENTED_OSS_PREFIX if batch_mode == 'word-segmented' else DEFAULT_OSS_PREFIX
    )

    manifest = load_or_create_manifest(
        manifest_path,
        words=words,
        provider=provider,
        model=request_model,
        cache_model=cache_model,
        voice=voice,
        book_ids=book_ids,
        package_size=package_size,
        content_mode=content_mode,
        reset_task=args.reset_task,
    )
    if args.reset_task:
        cleanup_stats = cleanup_word_audio_cache(
            cache_dir,
            manifest['words'],
            model=cache_model,
            voice=voice,
            word_tts_cache_path=word_tts_cache_path,
            normalize_word_key=normalize_word_key,
            task_name=task_name,
        )
        manifest = build_manifest(
            words,
            provider=provider,
            model=request_model,
            cache_model=cache_model,
            voice=voice,
            book_ids=book_ids,
            package_size=package_size,
            content_mode=content_mode,
        )
        json_dump(manifest_path, manifest)
        print(f'[Word TTS] cleanup={cleanup_stats}')

    progress = load_or_create_progress(progress_path, manifest=manifest, reset_task=args.reset_task)
    print(f'[Word TTS] cache_dir={cache_dir}')
    print(
        f'[Word TTS] mode={content_mode} provider={provider} '
        f'model={request_model} cache_model={cache_model} voice={voice}'
    )
    print(f'[Word TTS] book_ids={book_ids or "ALL"}')
    print(
        '[Word TTS] '
        f'total_words={manifest["total_words"]} '
        f'package_size={manifest["package_size"]} '
        f'total_packages={manifest["total_packages"]}'
    )
    print(f'[Word TTS] jobs={jobs} rate_interval={rate_interval:.1f}s backoff={backoff}')
    print(f'[Word TTS] manifest={manifest_path.name} progress={progress_path.name}')
    package_count = manifest['total_packages']
    packages = manifest['packages']
    words = manifest['words']
    start_package_index = (
        max(0, int(args.start_package))
        if args.start_package is not None
        else int(progress['next_package_index'])
    )
    if start_package_index > package_count:
        print(
            f'ERROR: start_package 超出范围，收到 {start_package_index}，总包数 {package_count}',
            file=sys.stderr,
        )
        return 1
    print(f'[Word TTS] start_package={start_package_index}')
    if args.upload_oss:
        axi_app_cli_root = Path(args.axi_app_cli_root).resolve()
        if not axi_app_cli_root.exists():
            print(f'ERROR: axi-app-cli 根目录不存在: {axi_app_cli_root}', file=sys.stderr)
            return 1
        print(f'[Word TTS] upload_oss=on prefix={oss_prefix} axi_root={axi_app_cli_root}')
    stop_after_packages = None if args.stop_after_packages is None else max(0, int(args.stop_after_packages))
    packages_processed = 0

    for package in packages[start_package_index:]:
        if stop_after_packages is not None and packages_processed >= stop_after_packages:
            break

        package_index = package['index']
        package_words = words[package['start']:package['end']]
        completed_before = count_cached_words(words[:package['start']], cache_dir, cache_model, voice)
        package_completed_start = count_cached_words(package_words, cache_dir, cache_model, voice)
        progress = _package_progress_update(
            progress_path,
            progress,
            status='running',
            next_package_index=package_index,
            current_package_index=package_index,
            current_package_completed=package_completed_start,
            current_package_total=package['count'],
            completed_words=completed_before + package_completed_start,
            current_word=None,
        )
        print(
            '[Word TTS] '
            f'package={package_index + 1}/{package_count} '
            f'range={package["start"]}:{package["end"]} '
            f'count={package["count"]}'
        )

        def on_package_progress(payload: dict) -> None:
            _package_progress_update(
                progress_path,
                progress,
                status='running',
                next_package_index=package_index,
                current_package_index=package_index,
                current_package_completed=payload['completed_final'],
                current_package_total=package['count'],
                completed_words=completed_before + payload['completed_final'],
                current_word=payload.get('current_word'),
            )

        stats = run_batch_generate_words(
            package_words,
            cache_dir=cache_dir,
            provider=provider,
            model=cache_model,
            voice=voice,
            content_mode=content_mode,
            phonetic_lookup=phonetic_lookup,
            concurrency=jobs,
            backoff_delays=backoff,
            rate_interval=rate_interval,
            progress_callback=on_package_progress,
        )
        package_verified = count_cached_words(package_words, cache_dir, cache_model, voice)
        if stats['errors'] or package_verified != package['count']:
            _package_progress_update(
                progress_path,
                progress,
                status='package_failed',
                next_package_index=package_index,
                current_package_index=package_index,
                current_package_completed=package_verified,
                current_package_total=package['count'],
                completed_words=completed_before + package_verified,
                current_word=None,
            )
            print(
                '[Word TTS] package_failed '
                f'package={package_index} errors={len(stats["errors"])} '
                f'verified={package_verified}/{package["count"]}',
                file=sys.stderr,
            )
            return 2

        if args.upload_oss:
            try:
                upload_summary = _upload_package_to_oss(
                    cache_dir=cache_dir,
                    package=package,
                    package_words=package_words,
                    cache_model=cache_model,
                    voice=voice,
                    normalize_word_key=normalize_word_key,
                    word_tts_cache_path=word_tts_cache_path,
                    oss_prefix=oss_prefix,
                    axi_app_cli_root=axi_app_cli_root,
                    upload_concurrency=jobs,
                    task_name=task_name,
                )
            except Exception as exc:
                update_progress(
                    progress_path,
                    progress,
                    status='upload_failed',
                    next_package_index=package_index,
                    current_package_index=package_index,
                    current_package_completed=package_verified,
                    current_package_total=package['count'],
                    completed_words=completed_before + package_verified,
                    current_word=None,
                    upload_error=str(exc),
                )
                print(
                    f'[Word TTS] upload_failed package={package_index}: {exc}',
                    file=sys.stderr,
                )
                return 2
            update_progress(
                progress_path,
                progress,
                last_uploaded_package_index=package_index,
                last_upload_bucket=upload_summary.get('bucket'),
                last_upload_count=upload_summary.get('uploadedCount'),
                last_upload_manifest_key=upload_summary.get('manifestObjectKey'),
                upload_error=None,
            )
            print(
                '[Word TTS] uploaded '
                f'package={package_index} '
                f'uploaded={upload_summary.get("uploadedCount")} '
                f'bucket={upload_summary.get("bucket")} '
                f'manifest={upload_summary.get("manifestObjectKey")}'
            )

        completed_package_indices = sorted({*progress.get('completed_package_indices', []), package_index})
        progress = _package_progress_update(
            progress_path,
            progress,
            status='running',
            next_package_index=package_index + 1,
            current_package_index=None,
            current_package_completed=0,
            current_package_total=0,
            completed_words=completed_before + package_verified,
            current_word=None,
            completed_package_indices=completed_package_indices,
        )
        packages_processed += 1

    if progress['next_package_index'] < package_count:
        _package_progress_update(
            progress_path,
            progress,
            status='paused',
            next_package_index=progress['next_package_index'],
            current_package_index=None,
            current_package_completed=0,
            current_package_total=0,
            completed_words=progress['completed_words'],
            current_word=None,
        )
        print(f'[Word TTS] paused next_package_index={progress["next_package_index"]}')
        return 0

    verification = verify_manifest_cache(
        words,
        cache_dir=cache_dir,
        model=cache_model,
        voice=voice,
        count_cached_words=count_cached_words,
        is_probably_valid_mp3_file=is_probably_valid_mp3_file,
        normalize_word_key=normalize_word_key,
        word_tts_cache_path=word_tts_cache_path,
        verification_path=verification_path,
    )
    if verification['verified_count'] != verification['expected_total']:
        _package_progress_update(
            progress_path,
            progress,
            status='verification_failed',
            next_package_index=package_count,
            current_package_index=None,
            current_package_completed=0,
            current_package_total=0,
            completed_words=verification['verified_count'],
            current_word=None,
        )
        print(
            '[Word TTS] verification_failed '
            f'{verification["verified_count"]}/{verification["expected_total"]}',
            file=sys.stderr,
        )
        return 2

    _package_progress_update(
        progress_path,
        progress,
        status='done',
        next_package_index=package_count,
        current_package_index=None,
        current_package_completed=0,
        current_package_total=0,
        completed_words=verification['verified_count'],
        current_word=None,
    )
    print(
        '[Word TTS] done '
        f'verified={verification["verified_count"]}/{verification["expected_total"]} '
        f'verification={verification_path.name}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
