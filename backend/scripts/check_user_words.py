"""One-off: compare chapter sum vs distinct word union for a user (e.g. luo)."""
import os
import sqlite3
import sys

def main():
    db = os.path.join(os.path.dirname(__file__), '..', 'database.sqlite')
    if not os.path.exists(db):
        print('database.sqlite not found at', db)
        sys.exit(1)
    name = sys.argv[1] if len(sys.argv) > 1 else 'luo'
    c = sqlite3.connect(db)
    cur = c.cursor()
    cur.execute(
        "SELECT id, username FROM users WHERE lower(username) LIKE ?",
        (f'%{name.lower()}%',),
    )
    rows = cur.fetchall()
    if not rows:
        print('no user matching', name)
        sys.exit(1)
    uid, uname = rows[0]
    print('user', uid, uname)
    cur.execute(
        'SELECT COALESCE(SUM(words_learned),0) FROM user_chapter_progress WHERE user_id=?',
        (uid,),
    )
    print('chapter_words_learned_sum', cur.fetchone()[0])
    cur.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT LOWER(TRIM(word)) AS w FROM user_smart_word_stats
            WHERE user_id=? AND word IS NOT NULL AND TRIM(word) != ''
            UNION
            SELECT LOWER(TRIM(word)) FROM user_quick_memory_records
            WHERE user_id=? AND word IS NOT NULL AND TRIM(word) != ''
            UNION
            SELECT LOWER(TRIM(word)) FROM user_wrong_words
            WHERE user_id=? AND word IS NOT NULL AND TRIM(word) != ''
        )
        """,
        (uid, uid, uid),
    )
    print('distinct_word_union', cur.fetchone()[0])
    for t in (
        'user_smart_word_stats',
        'user_quick_memory_records',
        'user_wrong_words',
    ):
        cur.execute(f'SELECT COUNT(*) FROM {t} WHERE user_id=?', (uid,))
        print(t, cur.fetchone()[0])
    c.close()

if __name__ == '__main__':
    main()
