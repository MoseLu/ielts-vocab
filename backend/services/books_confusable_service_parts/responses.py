def create_confusable_custom_chapters_response(user_id: int, groups):
    books = _books_module()
    try:
        normalized_groups = normalize_confusable_custom_groups(groups)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    resolved_groups, missing_words = resolve_confusable_group_words(normalized_groups)
    if missing_words:
        missing_summary = '、'.join(missing_words[:12])
        if len(missing_words) > 12:
            missing_summary += ' 等'
        return {
            'error': f'以下单词在现有词库中未找到完整音标或中文释义：{missing_summary}',
            'missing_words': missing_words,
        }, 400

    custom_book = get_confusable_custom_book(user_id, create=True)
    existing_chapter_count = len(custom_book.chapters)
    next_chapter_id = next_confusable_custom_chapter_id(custom_book)

    created_chapters = []
    total_words_added = 0
    for index, words in enumerate(resolved_groups, start=1):
        chapter_id = str(next_chapter_id + index - 1)
        chapter = books.CustomBookChapter(
            id=chapter_id,
            book_id=custom_book.id,
            title=build_confusable_custom_chapter_title(
                [word['word'] for word in words],
                existing_chapter_count + index,
            ),
            word_count=len(words),
            sort_order=existing_chapter_count + index - 1,
        )
        books.db.session.add(chapter)
        for word in words:
            books.db.session.add(books.CustomBookWord(
                chapter_id=chapter_id,
                word=word['word'],
                phonetic=word['phonetic'],
                pos=word['pos'],
                definition=word['definition'],
            ))

        total_words_added += len(words)
        created_chapters.append({
            'id': int(chapter_id),
            'title': chapter.title,
            'word_count': len(words),
            'group_count': 1,
            'is_custom': True,
        })

    custom_book.word_count = int(custom_book.word_count or 0) + total_words_added
    books.db.session.commit()
    return {
        'created_count': len(created_chapters),
        'created_chapters': created_chapters,
    }, 201


def update_confusable_custom_chapter_response(user_id: int, chapter_id: int, words_input):
    books = _books_module()
    custom_chapter = get_confusable_custom_chapter(user_id, chapter_id)
    if not custom_chapter:
        return {'error': '未找到可编辑的自定义易混组'}, 404

    try:
        groups = normalize_confusable_custom_groups([words_input])
    except ValueError as exc:
        return {'error': str(exc)}, 400

    resolved_groups, missing_words = resolve_confusable_group_words(groups)
    if missing_words:
        missing_summary = '、'.join(missing_words[:12])
        if len(missing_words) > 12:
            missing_summary += ' 等'
        return {
            'error': f'以下单词在现有词库中未找到完整音标或中文释义：{missing_summary}',
            'missing_words': missing_words,
        }, 400
    if not resolved_groups:
        return {'error': '请至少保留 2 个有效单词'}, 400

    resolved_words = resolved_groups[0]
    previous_word_count = int(custom_chapter.word_count or len(custom_chapter.words))
    custom_chapter.title = build_confusable_custom_chapter_title(
        [word['word'] for word in resolved_words],
        int(custom_chapter.sort_order or 0) + 1,
    )
    custom_chapter.word_count = len(resolved_words)

    for word in list(custom_chapter.words):
        books.db.session.delete(word)
    books.db.session.flush()

    for word in resolved_words:
        books.db.session.add(books.CustomBookWord(
            chapter_id=str(chapter_id),
            word=word['word'],
            phonetic=word['phonetic'],
            pos=word['pos'],
            definition=word['definition'],
        ))

    if custom_chapter.book:
        custom_chapter.book.word_count = max(
            0,
            int(custom_chapter.book.word_count or 0) - previous_word_count + len(resolved_words),
        )

    books.UserChapterProgress.query.filter_by(
        user_id=user_id,
        book_id=books.CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    ).delete()
    books.UserChapterModeProgress.query.filter_by(
        user_id=user_id,
        book_id=books.CONFUSABLE_MATCH_BOOK_ID,
        chapter_id=chapter_id,
    ).delete()

    books.db.session.commit()
    refreshed_chapter = get_confusable_custom_chapter(user_id, chapter_id)
    return {
        'chapter': {
            'id': chapter_id,
            'title': refreshed_chapter.title,
            'word_count': int(refreshed_chapter.word_count or len(refreshed_chapter.words)),
            'group_count': 1,
            'is_custom': True,
        },
        'words': serialize_confusable_custom_words(refreshed_chapter),
    }, 200
