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
reply is absent or contains unsupported media, it returns an explanation.
Both same-thread replies (`reply_to_message`) and cross-chat/topic replies
(`external_reply`) are supported, including voice, video circles, audio, and files
with an audio MIME type. External replies are answered on the command in the
requesting group/topic, never on an unrelated message ID in the source chat.
No recording is processed automatically in groups. Private access still uses
ALLOWED_USER_IDS; that list is not consulted for group requests.

If the bot says no usable audio was provided, its response includes a reason:
`reply_missing`, `reply_media_missing`, or `external_media_missing`. The matching
`Summary media unavailable` daemon log records only known field names and flags,
not messages, file IDs, keys, or transcripts. A screenshot cannot establish which
Telegram payload was received. If Telegram omits the recording, forward it into
the group and reply to that copy, or use an authorized private chat. Admin status
does not reconstruct media missing from Telegram's update.

After deploying, test a direct reply and a cross-topic reply in the previously
failing group, including a requester absent from ALLOWED_USER_IDS. Both should
work while OWNER_USER_ID is present; owner departure must block further requests.
If a reply still fails, retain the reason code and matching safe diagnostic line.
Forum topic replies preserve message_thread_id.

Telegram references:
- https://core.telegram.org/bots/faq#what-messages-will-my-bot-get
- https://core.telegram.org/bots/api#getchatmember
- https://core.telegram.org/bots/api#externalreplyinfo

## Settings and bilingual help

No BotFather command changes are required. At startup the bot registers `/start`,
`/help`, `/settings`, `/summary`, and `/id` with English and Russian descriptions.
If Telegram rejects command registration, typed commands still work and the daemon
logs a safe warning. The Telegram command list follows the Telegram app language;
the bot's own language switch controls message text and buttons.

`/start` and `/help` show the native English/Russian introduction and instructions.
`/settings` opens personal buttons for:

- Interface language: English / Русский (initially detected from Telegram).
- Detail: Quick gist / Key points / Detailed (default: Key points).
- Tone: Neutral / Casual / Professional (default: Neutral).

Choices apply to that person's requests in private and group chats. A group member
cannot change someone else's menu. Summary language always follows the recording,
independently of interface language. Tone changes wording, never facts or uncertainty.
Help and settings are available without paid access; they never grant processing
access or change ALLOWED_USER_IDS / OWNER_USER_ID authorization.

Summary buttons offer Shorter / More detail / Full transcript (Короче / Подробнее /
Полный текст). Detail buttons make a new summary request using the cached transcript,
without downloading or transcribing again, and do not change the saved detail setting.
These actions still require authorization, respect the 15-second cooldown, and expire
with the transcript (about an hour, or when the daemon restarts). Group actions use
the clicking person's preferences and remain visible to the group.

Preferences are stored in a small SQLite file, not in the transcript cache. Optional
`SETTINGS_DB_PATH` selects the file; the default is `/tmp/lazyfox-settings.sqlite3`,
which is writable by the Docker image's non-root user. It stores numeric user IDs,
language, detail and tone only—no recordings, transcripts, or API keys. SQLite files
are ignored by Git and excluded from the Docker context.

A process restart preserves settings only while that file survives. The default
container-local file is not durable across replacement/redeployment. To retain
preferences across deployments, configure SETTINGS_DB_PATH on persistent storage
that your host provides and make it writable by the container user; otherwise an
external database backend will be needed. This change does not provision storage
or add a new paid service. Keep the existing one-instance deployment.

After deploying, send `/start`, switch to Русский, choose detail and tone, and send
a recording. Check the summary and the Короче / Подробнее / Полный текст buttons.
Repeat in English and in a group from a non-allowlisted user while the owner is a
member. Check that another member cannot change your settings. Live Telegram and
OpenAI behavior must still be verified with your deployment.

## Privacy and limitations

- Recordings go from Telegram through your server to OpenAI. Consult the current
  OpenAI API data policy for provider retention; local deletion does not delete
  provider data or messages stored in Telegram.
- Temporary recordings are removed after processing, including on ordinary errors.
- Transcripts are cached only in process memory for approximately one hour, capped
  at 100 entries. Restarting loses them. Transcript buttons post the full text to
  the same chat, visible to its members.
- No saved history, translation button, subscriptions, or visual analysis in this version.
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
