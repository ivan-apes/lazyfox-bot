"""Validated per-user preferences. Never stores recordings or transcripts."""
import sqlite3
from pathlib import Path

OPTIONS = {
    'language': ('en', 'ru'),
    'detail': ('quick', 'points', 'detailed'),
    'tone': ('neutral', 'casual', 'professional'),
}


class Preferences:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS preferences '
                       '(user_id INTEGER PRIMARY KEY, language TEXT, detail TEXT, tone TEXT)')

    def get(self, user):
        language = 'ru' if user.get('language_code', '').lower().startswith('ru') else 'en'
        result = {'language': language, 'detail': 'points', 'tone': 'neutral'}
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT language, detail, tone FROM preferences WHERE user_id = ?',
                             (user['id'],)).fetchone()
        if row:
            for key, value in zip(OPTIONS, row):
                if value in OPTIONS[key]:
                    result[key] = value
        return result

    def set(self, user, key, value):
        if key not in OPTIONS or value not in OPTIONS[key]:
            raise ValueError('Invalid preference')
        settings = self.get(user)
        settings[key] = value
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO preferences (user_id, language, detail, tone) '
                       'VALUES (?, ?, ?, ?)',
                       (user['id'], settings['language'], settings['detail'], settings['tone']))
        return settings
