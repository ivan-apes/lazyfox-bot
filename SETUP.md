# Lazy Fox 🦊

Prepared for https://github.com/ivan-apes/lazyfox-bot .

## 1. Upload code

Download and extract lazyfox-bot.zip. On your GitHub repository page, choose
Add file → Upload files. Upload the extracted files themselves (not the ZIP,
and not a nested folder). Commit changes. Dockerfile and bot.py must be at
the repository root next to the existing README.

## 2. Railway

Choose GitHub Repository, connect GitHub if prompted, and allow Railway access
to only lazyfox-bot. Select that repository. In the service's Variables tab add:

| Variable | Value |
| --- | --- |
| TELEGRAM_BOT_TOKEN | Your BotFather token |
| OPENAI_API_KEY | Your OpenAI API key |
| OWNER_USER_ID | 0 initially |

Deploy the staged changes. Railway detects the Dockerfile. No domain, port,
database, healthcheck endpoint or public website is needed. Keep one replica
and disable serverless/sleep behavior if offered. Hosting is billed separately
from OpenAI; review the plan shown by Railway before subscribing.

## 3. Unlock your account

Open @lazyfox_summary_bot in Telegram. Press Start (or send /start).
It will reply with your numeric user ID. Set OWNER_USER_ID in Railway to that
number and deploy the change. Do not use your @username for this setting.
Until then, all paid processing is disabled. Never give the keys to the bot in chat.

OpenAI API billing must be enabled. If a project-restricted API key is used,
allow audio transcription and chat completions requests. Default models are
gpt-transcribe and gpt-4.1-mini; override TRANSCRIPTION_MODEL and SUMMARY_MODEL
in Railway if your account needs a different supported model. No silent fallback.

## 4. Test

Forward a short Russian voice message, then an English voice message, then a
video circle. Each should return a summary with a Full transcript button.
The summaries follow the recording's main language. Only spoken audio is analyzed.
Recordings must be under 20 MB and 20 minutes. A different private-chat user
should receive an access-locked message with no AI request.

## 5. Groups (optional)

Add the bot to a group and, as the owner, send /id in the group.
The bot replies with the group chat ID (often a negative number).
Add ALLOWED_CHAT_IDS in Railway, with this value. For multiple groups, separate
IDs with commas. Deploy the change. All human members of an allowed group can
use /summary; that usage is billed to your API account.

Reply to a voice message or circle with /summary (or /summary@lazyfox_summary_bot).
Group processing is on request, not automatic. For this workflow, Telegram's
default privacy mode can remain enabled: commands include the replied-to message.
The bot needs permission to send messages, but does not need administrator status.
If the group restricts commands or replies, check its settings.

## Privacy and limitations

- Recordings go from Telegram through your server to OpenAI. Consult the current
  OpenAI API data policy for provider retention; local deletion does not delete
  provider data or messages stored in Telegram.
- Temporary recordings are removed after processing, including on ordinary errors.
- Transcripts are cached only in process memory for approximately one hour, capped
  at 100 entries. Restarting loses them. Transcript buttons post the full text to
  the same chat, visible to its members.
- No saved history, translation button, subscriptions, visual analysis, or automatic
  summaries of private chats in this version.
- One recording is processed at a time. A 15-second per-user cooldown limits casual
  repeat requests; this is not a strict spending cap. No daily budget is enforced.
- Poll offsets are in memory. A crash before Telegram acknowledges an update can
  repeat a request. This starter is for personal use and small trusted groups;
  larger production use needs a persistent queue and deduplication.
- No live end-to-end test has been done with your keys. Deployment verification
  and the three recording tests above are still required.

## Troubleshooting

OpenAI HTTP 401: check the AI key. HTTP 403/404: check permissions/model access.
HTTP 429: check credits, billing and rate limits. Telegram HTTP 401: bot token.
Telegram HTTP 409: another copy of the bot is polling; stop it, keep one replica.
If the bot responds but access is locked, check OWNER_USER_ID and redeploy.

## Local checks (optional; not required on your PC)

python -m pip install -r requirements.txt
python -m unittest -v

Sources used for this version:
https://developers.openai.com/api/docs/guides/speech-to-text
https://developers.openai.com/api/docs/models/gpt-4.1-mini
https://core.telegram.org/bots/api
