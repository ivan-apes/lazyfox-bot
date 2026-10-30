# Lazy Fox 🦊

Telegram voice, video circle, and audio summarizer running as a Vercel daemon.
Forward recordings in private chats or reply to a group recording with
`/summary@your_bot_username`.

Private access uses `ALLOWED_USER_IDS`. Anyone in a group may request summaries
while `OWNER_USER_ID` is a member. Make the bot a group administrator for reliable
membership checks and command delivery.

See [SETUP.md](SETUP.md) for configuration, troubleshooting, and local checks.

Use `/start` or `/help` for instructions and `/settings` for English/Русский,
summary detail, and tone. Summaries follow the recording's language. Buttons let
you request a shorter or more detailed summary, or view the full transcript.
See SETUP.md for preference storage and deployment limitations.
