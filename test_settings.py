import time
import unittest
from unittest.mock import patch

import bot
from locales import TEXT
from preferences import Preferences
import test_bot


class SettingsTests(unittest.TestCase):
    setUp = test_bot.FoxTests.setUp
    telegram = test_bot.FoxTests.telegram
    # Reuse the isolated bot fixture, without inheriting all regression test methods.
    def callback(self, data, uid=123, language='en', message=None):
        return {'id': 'q', 'from': {'id': uid, 'language_code': language}, 'data': data,
                'message': message or {'chat': {'id': 123, 'type': 'private'}, 'message_id': 8}}

    def test_language_detection_explicit_override_and_storage_reopen(self):
        user = {'id': 123, 'language_code': 'ru-RU'}
        self.assertEqual(self.fox.settings(user), {'language': 'ru', 'detail': 'points', 'tone': 'neutral'})
        self.fox.preferences.set(user, 'language', 'en')
        self.fox.preferences.set(user, 'detail', 'detailed')
        self.fox.preferences.set(user, 'tone', 'professional')
        reopened = Preferences(self.fox.preferences.path)
        self.assertEqual(reopened.get(user), {'language': 'en', 'detail': 'detailed', 'tone': 'professional'})
        self.assertEqual(reopened.get({'id': 999, 'language_code': 'ru'})['detail'], 'points')

    def test_localization_keys_match_and_non_russian_defaults_english(self):
        self.assertEqual(set(TEXT['en']), set(TEXT['ru']))
        self.assertEqual(self.fox.settings({'id': 999, 'language_code': 'fr'})['language'], 'en')

    def test_settings_buttons_update_in_russian_without_paid_calls(self):
        self.fox.handle({'callback_query': self.callback('pref:123:language:ru')})
        self.assertEqual(self.fox.settings({'id': 123})['language'], 'ru')
        self.assertEqual(self.calls[-1][0], 'editMessageText')
        self.assertIn('Твои настройки', self.calls[-1][1]['text'])
        self.fox.handle({'callback_query': self.callback('pref:123:detail:quick')})
        self.fox.handle({'callback_query': self.callback('pref:123:tone:casual')})
        self.assertEqual(self.fox.settings({'id': 123}), {'language': 'ru', 'detail': 'quick', 'tone': 'casual'})
        for row in self.calls[-1][1]['reply_markup']['inline_keyboard']:
            for button in row:
                self.assertLessEqual(len(button['callback_data'].encode()), 64)

    def test_settings_cannot_change_someone_elses_preferences(self):
        self.fox.handle({'callback_query': self.callback('pref:999:tone:casual')})
        self.assertEqual(self.fox.settings({'id': 999})['tone'], 'neutral')
        self.assertEqual([method for method, _ in self.calls], ['answerCallbackQuery'])
        self.assertIn('someone else', self.calls[-1][1]['text'])

    def test_invalid_setting_does_not_write(self):
        self.fox.handle({'callback_query': self.callback('pref:123:tone:malicious')})
        self.assertEqual([method for method, _ in self.calls], ['answerCallbackQuery'])
        with self.assertRaises(ValueError):
            self.fox.preferences.set({'id': 123}, 'detail', 'malicious')

    def test_repeated_setting_is_idempotent(self):
        text, markup = self.fox.settings_panel({'id': 123})
        msg = {'chat': {'id': 123, 'type': 'private'}, 'message_id': 8,
               'text': text, 'reply_markup': markup}
        self.fox.handle({'callback_query': self.callback('pref:123:detail:points', message=msg)})
        self.assertEqual([method for method, _ in self.calls], ['answerCallbackQuery'])

    def test_onboarding_help_settings_and_ids_are_localized_and_no_paid_processing(self):
        self.fox.process = lambda *args: self.fail('help processing')
        for language, expected in [('en', 'In private'), ('ru', 'В личном чате')]:
            msg = {'chat': {'type': 'group', 'id': -456}, 'from': {'id': 999, 'language_code': language},
                   'message_id': 4, 'message_thread_id': 7, 'text': '/start'}
            self.fox.handle({'message': msg})
            self.assertIn(expected, self.calls[-1][1]['text'])
            self.assertEqual(self.calls[-1][1]['message_thread_id'], 7)
            msg['text'] = '/settings'
            self.fox.handle({'message': msg})
            self.assertIn(TEXT[language]['points'], self.calls[-1][1]['text'])
            msg['text'] = '/id'
            self.fox.handle({'message': msg})
            self.assertIn('999', self.calls[-1][1]['text'])

    def test_prompt_uses_all_detail_and_tone_choices_without_translating(self):
        for detail in ('quick', 'points', 'detailed'):
            for tone in ('neutral', 'casual', 'professional'):
                with patch.object(self.fox, 'ai', return_value={'choices': [{'message': {'content': 'summary'}}]}) as ai:
                    self.fox.summarize('untrusted transcript', {'language': 'ru', 'detail': detail, 'tone': tone})
                payload = ai.call_args.kwargs['json']
                self.assertEqual(payload['messages'][1]['content'], 'untrusted transcript')
                self.assertIn('independently of interface language', payload['messages'][0]['content'])
                self.assertIn('Tone must never change the facts', payload['messages'][0]['content'])
                self.assertEqual(payload['max_tokens'], {'quick': 200, 'points': 700, 'detailed': 1200}[detail])
                self.assertFalse(payload['store'])

    def test_shorter_uses_cached_transcript_clickers_tone_and_original_topic(self):
        self.fox.cache['tag'] = (time.monotonic()+60, -456, 'cached transcript')
        self.fox.preferences.set({'id': 999}, 'tone', 'casual')
        msg = {'chat': {'id': -456, 'type': 'supergroup'}, 'message_id': 8, 'message_thread_id': 7}
        with patch.object(self.fox, 'summarize', return_value='Коротко') as summarize:
            self.fox.handle({'callback_query': self.callback('sum:tag:quick', uid=999, language='ru', message=msg)})
        # The saved tone also saved the default interface language at the time.
        summarize.assert_called_once_with('cached transcript', {'language': 'en', 'detail': 'quick', 'tone': 'casual'})
        self.assertEqual(self.calls[-1][1]['message_thread_id'], 7)
        self.assertEqual(self.calls[-1][1]['chat_id'], -456)
        self.assertEqual(self.fox.settings({'id': 999})['detail'], 'points')
        with patch.object(self.fox, 'summarize') as summarize:
            self.fox.handle({'callback_query': self.callback('sum:tag:detailed', uid=999, message=msg)})
            summarize.assert_not_called()
        self.assertIn('15 seconds', self.calls[-1][1]['text'])

    def test_adjustment_rechecks_authorization_chat_and_expiry(self):
        msg = {'chat': {'id': -456, 'type': 'supergroup'}, 'message_id': 8}
        for expiry, chat, member in [(time.monotonic()+60, -999, 'member'),
                                     (time.monotonic()-1, -456, 'member'),
                                     (time.monotonic()+60, -456, 'left')]:
            self.fox.cache['tag'] = (expiry, chat, 'transcript')
            with patch.object(self.fox, 'tg', return_value={'status': member}), patch.object(self.fox, 'summarize') as summarize:
                self.fox.handle({'callback_query': self.callback('sum:tag:quick', uid=999, message=msg)})
                summarize.assert_not_called()

    def test_russian_processing_errors_and_buttons(self):
        msg = {'chat': {'id': -456, 'type': 'supergroup'}, 'from': {'id': 999, 'language_code': 'ru'},
               'message_id': 4, 'text': '/summary'}
        self.fox.handle({'message': msg})
        self.assertIn('не вижу запись', self.calls[-1][1]['text'])
        self.fox.process(msg, {'message_id': 3, 'voice': {'file_size': 20000001}})
        self.assertIn('20 МБ', self.calls[-1][1]['text'])
        buttons = self.fox.summary_buttons('tag', 'ru')['inline_keyboard']
        self.assertEqual(buttons[0][0]['text'], 'Короче')
        self.assertEqual(buttons[1][0]['text'], 'Полный текст')

    def test_registers_default_english_and_russian_command_menus(self):
        self.fox.register_commands()
        self.assertEqual([data['language_code'] for _, data in self.calls], ['', 'en', 'ru'])
        self.assertEqual({c['command'] for c in self.calls[-1][1]['commands']}, {'start', 'help', 'settings', 'summary', 'id'})

    def test_settings_never_unlock_private_processing(self):
        user = {'id': 999, 'language_code': 'ru'}
        self.fox.handle({'callback_query': self.callback('pref:999:tone:casual', uid=999, language='ru')})
        self.fox.process = lambda *args: self.fail('settings granted paid access')
        self.fox.handle({'message': {'chat': {'type': 'private', 'id': 999}, 'from': user,
                         'message_id': 4, 'voice': {'file_id': 'recording'}}})
        self.assertIn('по приглашению', self.calls[-1][1]['text'])

    def test_adjustment_failure_returns_localized_error_without_exception_details(self):
        self.fox.cache['tag'] = (time.monotonic()+60, 123, 'transcript')
        with patch.object(self.fox, 'summarize', side_effect=RuntimeError('SECRET-EXCEPTION')):
            with self.assertLogs('lazyfox', level='WARNING') as logs:
                self.fox.handle({'callback_query': self.callback('sum:tag:quick', language='ru')})
        self.assertIn('Не удалось обработать', self.calls[-1][1]['text'])
        self.assertNotIn('SECRET-EXCEPTION', str(self.calls))
        self.assertNotIn('SECRET-EXCEPTION', str(logs.output))

    def test_russian_summary_keeps_button_data_compatible_with_transcript_cache(self):
        self.fox.cache['tag'] = (time.monotonic()+60, 123, 'Полный исходный текст')
        self.fox.handle({'callback_query': self.callback('tag', language='ru')})
        self.assertEqual(self.calls[-1][1]['text'], 'Полный исходный текст')
