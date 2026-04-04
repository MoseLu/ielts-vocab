from collections.abc import Iterable, MutableMapping
from pathlib import Path
from typing import Any


def load_split_module_parts(
    module_file: str,
    relative_paths: Iterable[str],
    namespace: MutableMapping[str, Any],
) -> None:
    module_dir = Path(module_file).resolve().parent
    for relative_path in relative_paths:
        part_path = module_dir / relative_path
        exec(compile(part_path.read_text(encoding='utf-8'), str(part_path), 'exec'), namespace)
