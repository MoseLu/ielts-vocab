from pathlib import Path


def _load_part(relative_path: str) -> None:
    part_path = Path(__file__).with_suffix('').parent / relative_path
    exec(compile(part_path.read_text(encoding='utf-8'), str(part_path), 'exec'), globals())


_load_part('generate_confusable_book_steps/core.py')
_load_part('generate_confusable_book_steps/group_builders.py')
_load_part('generate_confusable_book_steps/high_value_listening.py')
_load_part('generate_confusable_book_steps/cli.py')

del _load_part
