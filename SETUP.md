# Lazy Fox 🦊

Prepared for https://github.com/ivan-apes/lazyfox-bot .

## 1. Repository and deployment

The bot runs as one long-polling process. The checked-in `vercel.json` configures
a Vercel daemon using `Dockerfile`, with one instance in `iad1`. Keep only one
polling instance and do not run a local copy against the same bot token.
`railway.toml` is an alternative deployment configuration.

## 2. Environment

Set these in your deployment's environment settings, never in source control:

| Variable | Value |
| --- | --- |
| TELEGRAM_BOT_TOKEN | Your BotFather token |
| OPENAI_API_KEY | Your OpenAI API key |
| ALLOWED_USER_IDS | Comma-separated numeric IDs allowed in private chats |
| OWNER_USER_ID | Numeric ID whose group membership enables group summaries |

Redeploy after changing environment variables. Private access does not implicitly
include OWNER_USER_ID: add that ID to ALLOWED_USER_IDS if needed. An empty private
allowlist locks all private processing. OWNER_USER_ID=0 disables group processing.
No group allowlist is used; ALLOWED_CHAT_IDS is obsolete.

## 3. Unlock your account

Open your bot in Telegram and send /start. It replies with your numeric user ID.
Add that number to ALLOWED_USER_IDS for private access and set OWNER_USER_ID for
group authorization. Do not use an @username. Never send keys to the bot in chat.

OpenAI API billing must be enabled. If a project-restricted API key is used,
allow audio transcription and chat completions requests. Default models are
gpt-transcribe and gpt-4.1-mini; override TRANSCRIPTION_MODEL and SUMMARY_MODEL
in the deployment environment if your account needs a different supported model. No silent fallback.

## 4. Test

Forward a short Russian voice message, then an English voice message, then a
video circle. Each should return a summary with a Full transcript button.
The summaries follow the recording's main language. Only spoken audio is analyzed.
Recordings must be under 20 MB and 20 minutes. A different private-chat user
should receive an access-locked message with no AI request.

## 5. Groups (optional)

Add the bot to a group and make it an administrator. Anyone in that group may
request a summary while OWNER_USER_ID is a current member. Membership is checked
for every request and transcript button; left/kicked owners disable access.
Restricted owners count only when Telegram reports is_member=true. A failed check
blocks processing and returns a diagnostic; it never falls back to allowing access.

Reply directly to a voice message, video circle, or audio message with
/summary@your_bot_username. Bare /summary works only when Telegram delivers it.
With privacy mode enabled, unaddressed commands are not always delivered, especially
in groups with multiple bots. Replies to another bot's messages can also be routed
to that other bot. Making this bot an administrator makes delivery and membership
checks reliable. Alternatively, disabling privacy mode improves delivery but does
not guarantee owner membership lookups without administrator status.

Group processing is only on request. The reply payload supplies the recording;
the bot does not fetch old messages or require a prior cached recording. If the
reply is absent or contains unsupported media, it returns usage instructions.
Forum topic replies preserve message_thread_id.

Telegram references:
- https://core.telegram.org/bots/faq#what-messages-will-my-bot-get
- https://core.telegram.org/bots/api#getchatmember

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
If the bot responds but access is locked, check ALLOWED_USER_IDS for private chats and OWNER_USER_ID membership for groups, then redeploy.

## Local checks (optional; not required on your PC)

python -m pip install -r requirements.txt
python -m unittest -v

Sources used for this version:
https://developers.openai.com/api/docs/guides/speech-to-text
https://developers.openai.com/api/docs/models/gpt-4.1-mini
https://core.telegram.org/bots/api
