import unittest
from unittest.mock import patch
import bot


class FoxTests(unittest.TestCase):
    def setUp(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test', 'OPENAI_API_KEY': 'test', 'OWNER_USER_ID': '123', 'ALLOWED_CHAT_IDS': '-456'}):
            self.fox = bot.Fox()
        self.calls = []
        self.fox.tg = lambda method, **data: self.calls.append((method, data))

    def test_locked_by_default(self):
        self.assertFalse(bot.authorized({'chat': {'type': 'private'}, 'from': {'id': 123}}, 0, set()))
        self.assertFalse(bot.authorized({'chat': {'type': 'group', 'id': -456}, 'from': {'id': 123}}, 0, {-456}))

    def test_private_owner_only_and_group_allowlist(self):
        self.assertTrue(bot.authorized({'chat': {'type': 'private'}, 'from': {'id': 123}}, 123, set()))
        self.assertFalse(bot.authorized({'chat': {'type': 'private'}, 'from': {'id': 999}}, 123, set()))
        self.assertTrue(bot.authorized({'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999}}, 123, {-456}))
        self.assertFalse(bot.authorized({'chat': {'type': 'group', 'id': -999}, 'from': {'id': 123}}, 123, {-456}))

    def test_no_paid_call_for_unauthorized(self):
        self.fox.process = lambda *args: self.fail('unauthorized processing')
        self.fox.handle({'message': {'chat': {'type': 'private', 'id': 999}, 'from': {'id': 999}, 'message_id': 1, 'voice': {'file_id': 'x'}}})

    def test_group_requires_command(self):
        self.fox.process = lambda *args: self.fail('automatic group processing')
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456}, 'from': {'id': 999}, 'message_id': 1, 'voice': {'file_id': 'x'}}})

    def test_summary_command_targets_reply(self):
        source = {'message_id': 3, 'video_note': {'file_id': 'x'}}
        captured = []
        self.fox.process = lambda msg, original: captured.append(original)
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456}, 'from': {'id': 999}, 'message_id': 4, 'text': '/summary', 'reply_to_message': source}})
        self.assertEqual(captured, [source])

    def test_oversize_never_calls_ai(self):
        self.fox.ai = lambda *a, **kw: self.fail('oversize paid call')
        self.fox.process({'chat': {'id': 123}, 'from': {'id': 123}, 'message_id': 1}, {'voice': {'file_size': 20000001}, 'message_id': 1})
        self.assertIn('20 MB', self.calls[0][1]['text'])

    def test_callback_cannot_cross_chats(self):
        self.fox.cache['tag'] = (bot.time.monotonic()+60, 777, 'private transcript')
        self.fox.handle({'callback_query': {'id': 'q', 'from': {'id': 123}, 'data': 'tag', 'message': {'chat': {'id': 123, 'type': 'private'}, 'message_id': 1}}})
        self.assertEqual([c[0] for c in self.calls], ['answerCallbackQuery'])

    def test_unicode_splits_losslessly(self):
        text = '🦊Привет' * 1000
        parts = bot.chunks(text)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(p.encode('utf-16-le')) // 2 <= 4096 for p in parts))


if __name__ == '__main__':
    unittest.main()
