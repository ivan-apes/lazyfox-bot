import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from types import SimpleNamespace
import bot


class FoxTests(unittest.TestCase):
    def setUp(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test', 'OPENAI_API_KEY': 'test', 'OWNER_USER_ID': '123', 'ALLOWED_USER_IDS': '123,321'}):
            self.fox = bot.Fox()
        self.calls = []
        self.fox.username = 'lazyfox_summary_bot'
        self.fox.tg = self.telegram

    def telegram(self, method, **data):
        self.calls.append((method, data))
        if method == 'getChatMember':
            return {'status': 'member'}

    def test_private_allowlist_independent_of_owner(self):
        self.fox.owner = 0
        for uid, expected in [(123, True), (321, True), (999, False)]:
            self.assertEqual(self.fox.authorized({'chat': {'type': 'private'}, 'from': {'id': uid}}), expected)
        self.fox.allowed_users = set()
        self.fox.owner = 123
        self.assertFalse(self.fox.authorized({'chat': {'type': 'private'}, 'from': {'id': 123}}))
        self.assertEqual(self.calls, [])

    def test_group_membership_statuses(self):
        message = {'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999}}
        for status, is_member, expected in [
            ('creator', False, True), ('administrator', False, True),
            ('member', False, True), ('restricted', True, True),
            ('restricted', False, False), ('left', False, False), ('kicked', False, False),
        ]:
            with self.subTest(status=status, is_member=is_member):
                with patch.object(self.fox, 'tg', return_value={'status': status, 'is_member': is_member}) as tg:
                    self.assertEqual(self.fox.authorized(message), expected)
                    tg.assert_called_once_with('getChatMember', chat_id=-456, user_id=123)
        self.fox.owner = 0
        self.assertFalse(self.fox.authorized(message))
        self.fox.owner = 123
        message['from']['is_bot'] = True
        self.assertFalse(self.fox.authorized(message))

    def test_membership_failure_is_visible_and_no_processing(self):
        self.fox.process = lambda *args: self.fail('unverified access')
        original = self.fox.tg
        def telegram(method, **data):
            if method == 'getChatMember':
                raise bot.ServiceError('Telegram getChatMember: HTTP 400')
            return original(method, **data)
        self.fox.tg = telegram
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456},
                         'from': {'id': 999}, 'message_id': 4, 'text': '/summary'}})
        self.assertIn('Cannot verify', self.calls[-1][1]['text'])

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

    def test_reply_media_variants_and_explicit_command(self):
        for kind in ('voice', 'video_note', 'audio'):
            source = {'message_id': 3, kind: {'file_id': 'x'}}
            with patch.object(self.fox, 'process') as process:
                msg = {'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999},
                       'message_id': 4, 'message_thread_id': 7,
                       'text': '/summary@LazyFox_summary_bot', 'reply_to_message': source}
                self.fox.handle({'message': msg})
                process.assert_called_once_with(msg, source)

    def test_commands_for_other_bots_are_ignored(self):
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456},
                         'from': {'id': 999}, 'message_id': 4, 'text': '/summary@other_bot'}})
        self.assertEqual(self.calls, [])

    def test_forwarded_private_recording(self):
        msg = {'chat': {'type': 'private', 'id': 123}, 'from': {'id': 123},
               'message_id': 1, 'voice': {'file_id': 'x'}, 'forward_origin': {'type': 'hidden_user'}}
        with patch.object(self.fox, 'process') as process:
            self.fox.handle({'message': msg})
            process.assert_called_once_with(msg, msg)

    def test_missing_reply_gets_instructions(self):
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456},
                         'from': {'id': 999}, 'message_id': 4, 'text': '/summary'}})
        self.assertIn('Reply to', self.calls[-1][1]['text'])

    def test_topic_reply_parameters(self):
        self.fox.send(-456, 'summary', reply=3, thread=7)
        self.assertEqual(self.calls[-1], ('sendMessage', {
            'chat_id': -456, 'text': 'summary', 'message_thread_id': 7,
            'reply_parameters': {'message_id': 3, 'allow_sending_without_reply': True}}))

    def test_oversize_never_calls_ai(self):
        self.fox.ai = lambda *a, **kw: self.fail('oversize paid call')
        self.fox.process({'chat': {'id': 123}, 'from': {'id': 123}, 'message_id': 1}, {'voice': {'file_size': 20000001}, 'message_id': 1})
        self.assertIn('20 MB', self.calls[0][1]['text'])

    def test_callback_cannot_cross_chats(self):
        self.fox.cache['tag'] = (bot.time.monotonic()+60, 777, 'private transcript')
        self.fox.handle({'callback_query': {'id': 'q', 'from': {'id': 123}, 'data': 'tag', 'message': {'chat': {'id': 123, 'type': 'private'}, 'message_id': 1}}})
        self.assertEqual([c[0] for c in self.calls], ['answerCallbackQuery'])

    def test_owner_leaving_revokes_summary_and_transcript(self):
        self.fox.process = lambda *args: self.fail('owner left')
        self.fox.cache['tag'] = (bot.time.monotonic()+60, -456, 'transcript')
        original = self.fox.tg
        def telegram(method, **data):
            if method == 'getChatMember':
                return {'status': 'left'}
            return original(method, **data)
        self.fox.tg = telegram
        self.fox.handle({'message': {'chat': {'type': 'group', 'id': -456},
                         'from': {'id': 999}, 'message_id': 4, 'text': '/summary'}})
        self.assertIn('current member', self.calls[-1][1]['text'])
        self.calls.clear()
        self.fox.handle({'callback_query': {'id': 'q', 'from': {'id': 999}, 'data': 'tag',
                         'message': {'chat': {'id': -456, 'type': 'group'}, 'message_id': 1}}})
        self.assertEqual([c[0] for c in self.calls], ['answerCallbackQuery'])

    def test_external_reply_media_with_and_without_origin_message_id(self):
        for kind in ('voice', 'video_note', 'audio', 'document'):
            for original_id in (None, 88):
                with self.subTest(kind=kind, original_id=original_id):
                    recording = {'file_id': 'external-file', 'mime_type': 'audio/ogg'}
                    external = {'origin': {'type': 'hidden_user'}, kind: recording}
                    if original_id:
                        external.update(message_id=original_id, chat={'id': -999})
                    msg = {'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999},
                           'message_id': 4, 'message_thread_id': 7, 'text': '/summary',
                           'external_reply': external}
                    with patch.object(self.fox, 'process') as process:
                        self.fox.handle({'message': msg})
                        source = process.call_args.args[1]
                        self.assertEqual(bot.media(source), recording)
                        self.assertEqual(source['message_id'], 4)
                    self.assertEqual(external.get('message_id'), original_id)

    def test_direct_reply_preferred_over_external_reply(self):
        reply = {'message_id': 3, 'voice': {'file_id': 'direct'}}
        msg = {'message_id': 4, 'reply_to_message': reply,
               'external_reply': {'voice': {'file_id': 'external'}}}
        self.assertIs(bot.reply_source(msg), reply)

    def test_audio_documents_supported_but_other_documents_not_processed(self):
        audio = {'file_id': 'audio-file', 'mime_type': 'audio/ogg'}
        self.assertEqual(bot.media({'document': audio}), audio)
        self.assertIsNone(bot.media({'document': {'file_id': 'pdf', 'mime_type': 'application/pdf'}}))

    def test_group_access_does_not_depend_on_private_allowlist_or_group_id(self):
        self.fox.allowed_users.clear()
        for chat_type, chat_id in [('group', -100), ('supergroup', -200)]:
            msg = {'chat': {'type': chat_type, 'id': chat_id}, 'from': {'id': 999},
                   'message_id': 4, 'text': '/summary',
                   'external_reply': {'voice': {'file_id': 'external'}}}
            with patch.object(self.fox, 'process') as process:
                self.fox.handle({'message': msg})
                process.assert_called_once()
        with patch.object(self.fox, 'tg', return_value={'status': 'left'}):
            with patch.object(self.fox, 'process') as process:
                self.fox.handle({'message': msg})
                process.assert_not_called()

    def test_unavailable_media_diagnostics_never_process_or_log_content(self):
        for field, reason in [('external_reply', 'external_media_missing'),
                              ('reply_to_message', 'reply_media_missing')]:
            msg = {'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999},
                   'message_id': 4, 'message_thread_id': 7, 'text': '/summary',
                   field: {'message_id': 3, 'text': 'PRIVATE-CONTENT',
                           'document': {'file_id': 'SECRET-FILE-ID', 'mime_type': 'application/pdf'}}}
            with patch.object(self.fox, 'ai', side_effect=AssertionError('paid call')):
                with self.assertLogs('lazyfox', level='INFO') as logs:
                    self.fox.handle({'message': msg})
            self.assertIn(reason, self.calls[-1][1]['text'])
            self.assertEqual(self.calls[-1][1]['message_thread_id'], 7)
            self.assertNotIn('PRIVATE-CONTENT', str(logs.output))
            self.assertNotIn('SECRET-FILE-ID', str(logs.output))

    def test_external_reply_runs_pipeline_and_replies_in_requesting_topic(self):
        msg = {'chat': {'type': 'supergroup', 'id': -456}, 'from': {'id': 999},
               'message_id': 4, 'message_thread_id': 7, 'text': '/summary',
               'external_reply': {'message_id': 88, 'chat': {'id': -999},
                                  'voice': {'file_id': 'external-file', 'duration': 1}}}
        original = self.fox.tg
        def telegram(method, **data):
            if method == 'getFile':
                self.assertEqual(data['file_id'], 'external-file')
                return {'file_path': 'recording.ogg', 'file_size': 10}
            return original(method, **data)
        self.fox.tg = telegram
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [b'recording']
        def convert(args, **kwargs):
            if args[0] == 'ffmpeg':
                Path(args[-1]).write_bytes(b'audio')
            return SimpleNamespace(stdout=b'1.0')
        with patch('bot.requests.get', return_value=response), patch('bot.subprocess.run', side_effect=convert):
            with patch.object(self.fox, 'ai', return_value={'text': 'spoken words'}) as ai:
                with patch.object(self.fox, 'summarize', return_value='summary') as summarize:
                    self.fox.handle({'message': msg})
        ai.assert_called_once()
        summarize.assert_called_once_with('spoken words')
        messages = [data for method, data in self.calls if method == 'sendMessage']
        self.assertEqual(len(messages), 2)
        for data in messages:
            self.assertEqual(data['chat_id'], -456)
            self.assertEqual(data['message_thread_id'], 7)
            self.assertEqual(data['reply_parameters']['message_id'], 4)
        self.assertIn('summary', messages[-1]['text'])

    def test_unicode_splits_losslessly(self):
        text = '🦊Привет' * 1000
        parts = bot.chunks(text)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(p.encode('utf-16-le')) // 2 <= 4096 for p in parts))


if __name__ == '__main__':
    unittest.main()
