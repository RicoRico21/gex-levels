"""Telegram front end - long-polls for messages and replies.

No webhook, no public URL, no hosting required. Run it on your laptop or a
cheap VPS and message the bot from your phone.
"""

import time

import requests

from .. import brain, config, transcribe

API = "https://api.telegram.org/bot{token}/{method}"
FILE_API = "https://api.telegram.org/file/bot{token}/{path}"
POLL_TIMEOUT = 50
TELEGRAM_MAX_CHARS = 4096

# Conversation history per chat, kept in memory. Durable memory is the vault -
# this is just so follow-up messages make sense within a session.
_histories: dict[str, list] = {}


def _call(method: str, **params):
    url = API.format(token=config.TELEGRAM_BOT_TOKEN, method=method)
    response = requests.post(url, json=params, timeout=POLL_TIMEOUT + 10)
    response.raise_for_status()
    return response.json()


def _send(chat_id: str, text: str) -> None:
    for start in range(0, len(text), TELEGRAM_MAX_CHARS):
        _call("sendMessage", chat_id=chat_id, text=text[start : start + TELEGRAM_MAX_CHARS])


def _typing(chat_id: str) -> None:
    """Show the typing indicator - a turn with tool calls can take a while."""
    try:
        _call("sendChatAction", chat_id=chat_id, action="typing")
    except Exception:
        pass  # cosmetic only, never worth failing a turn over


def _download(file_id: str) -> bytes:
    """Pull a file (a voice note) off Telegram's servers."""
    file_path = _call("getFile", file_id=file_id)["result"]["file_path"]
    url = FILE_API.format(token=config.TELEGRAM_BOT_TOKEN, path=file_path)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def _voice_to_text(chat_id: str, message: dict) -> str | None:
    """Turn a voice note into text, or explain why we can't and return None."""
    voice = message.get("voice") or message.get("audio") or message.get("video_note")
    if not voice:
        return None
    if not transcribe.available():
        _send(
            chat_id,
            "I can't hear voice notes yet - transcription isn't configured. "
            "See SETUP.md step 7, or just send text.",
        )
        return None
    _typing(chat_id)
    try:
        audio = _download(voice["file_id"])
        text = transcribe.transcribe(audio)
    except Exception as exc:
        _send(chat_id, f"Couldn't transcribe that: {exc}")
        return None
    if not text:
        _send(chat_id, "That came through empty - try again?")
        return None
    return text


def _authorised(chat_id: str) -> bool:
    if not config.TELEGRAM_ALLOWED_IDS:
        # First run: nothing is locked down yet, so tell the owner how to.
        print(
            f"[jarvis] message from chat id {chat_id}. Add it to "
            f"JARVIS_TELEGRAM_ALLOWED_IDS in .env to lock the bot to you."
        )
        return True
    return chat_id in config.TELEGRAM_ALLOWED_IDS


def _handle(message: dict) -> None:
    chat_id = str(message["chat"]["id"])
    if not _authorised(chat_id):
        return

    text = message.get("text", "") or _voice_to_text(chat_id, message) or ""
    if not text:
        return
    if text.startswith("/start"):
        _send(chat_id, "Jarvis is up. Ask me for content, a plan, a market read, or a client email.")
        return
    if text.startswith("/reset"):
        _histories.pop(chat_id, None)
        _send(chat_id, "Conversation cleared. The vault still remembers everything.")
        return

    _typing(chat_id)
    try:
        reply, _histories[chat_id] = brain.think(text, _histories.get(chat_id, []))
    except Exception as exc:  # keep the bot alive through any one bad turn
        print(f"[jarvis] error handling message: {exc!r}")
        _send(chat_id, f"That one broke: {exc}")
        return
    _send(chat_id, reply)


def run() -> int:
    if not config.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set - add it to .env (get one from @BotFather).")
        return 1

    config.ensure_dirs()
    print("[jarvis] listening on Telegram. Ctrl-C to stop.")
    offset = None
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            updates = _call("getUpdates", **params).get("result", [])
        except KeyboardInterrupt:
            print("\n[jarvis] stopped.")
            return 0
        except Exception as exc:
            print(f"[jarvis] poll failed ({exc!r}), retrying in 5s")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if message:
                _handle(message)


if __name__ == "__main__":
    raise SystemExit(run())
