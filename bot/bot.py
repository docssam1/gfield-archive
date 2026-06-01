from __future__ import annotations

import datetime as dt
import os
import pathlib
import shlex
import subprocess
from typing import Final

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


BASE_DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR: Final[pathlib.Path] = BASE_DIR / "gfield_output"
LOG_DIR: Final[pathlib.Path] = OUT_DIR / "logs"
SCRIPTS_DIR: Final[pathlib.Path] = BASE_DIR / "scripts"

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "").strip()

ALLOWED_CMDS: Final[dict[str, list[str]]] = {
    "server_info": ["bash", "scripts/server_info.sh"],
    "folder_list": ["bash", "scripts/folder_list.sh"],
    "full_status": ["bash", "scripts/full_status.sh"],
}

ALIASES: Final[dict[str, str]] = {
    "서버정보": "server_info",
    "폴더목록": "folder_list",
    "전체상태": "full_status",
    "serverinfo": "server_info",
    "folders": "folder_list",
    "statusall": "full_status",
}


def _is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_ID:
        return True
    if update.effective_chat is None:
        return False
    return str(update.effective_chat.id) == ALLOWED_CHAT_ID


async def _guard(update: Update) -> bool:
    if _is_allowed(update):
        return True
    await update.message.reply_text("Unauthorized chat.")
    return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.message.reply_text(
        "GFIELD bot online.\n"
        "Commands: /status /run_preview /last_report\n"
        "Run commands: /run 서버정보 | /run 폴더목록 | /run 전체상태"
    )


def _normalize_run_target(raw: str) -> str:
    target = raw.strip()
    if not target:
        return ""
    return ALIASES.get(target, target)


async def _run_allowed_command(update: Update, name: str) -> None:
    if name not in ALLOWED_CMDS:
        await update.message.reply_text(
            "Unknown run target.\n"
            "Use: /run 서버정보 | /run 폴더목록 | /run 전체상태"
        )
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"run_{name}_{ts}.log"

    cmd = ALLOWED_CMDS[name]
    await update.message.reply_text(f"Running: {name}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        merged = "\n".join(
            [
                f"time={dt.datetime.now().isoformat()}",
                f"cmd={' '.join(cmd)}",
                f"returncode={proc.returncode}",
                "---- stdout ----",
                proc.stdout or "",
                "---- stderr ----",
                proc.stderr or "",
            ]
        )
        log_path.write_text(merged, encoding="utf-8")
        preview = (proc.stdout or proc.stderr or "(no output)").strip()
        if len(preview) > 3200:
            preview = preview[:3200] + "\n... (truncated)"
        await update.message.reply_text(
            f"Done: {name}\nreturncode={proc.returncode}\nlog={log_path.as_posix()}\n\n{preview}"
        )
    except Exception as exc:  # noqa: BLE001
        log_path.write_text(f"error={type(exc).__name__}: {exc}\n", encoding="utf-8")
        await update.message.reply_text(f"Run failed: {type(exc).__name__}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    report = OUT_DIR / "GFIELD_V3_FULL_AUTO_FINAL_REPORT.txt"
    auth_note = OUT_DIR / "google_drive_auth_needed_v3.txt"
    lines = [
        f"time={dt.datetime.now().isoformat(timespec='seconds')}",
        f"report_exists={report.exists()}",
        f"auth_deferred_note={auth_note.exists()}",
        "mode=PREVIEW_ONLY",
        "db_update=disabled",
        "parent_sending=disabled",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_run_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"manual_preview_{ts}.log"

    cmd = ["python", "./gfield_output/scripts/future_textbook_inventory_runner_v3.py"]
    await update.message.reply_text("Running preview task...")
    try:
        proc = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        log_path.write_text(
            "\n".join(
                [
                    f"time={dt.datetime.now().isoformat()}",
                    f"cmd={' '.join(cmd)}",
                    f"returncode={proc.returncode}",
                    "---- stdout ----",
                    proc.stdout or "",
                    "---- stderr ----",
                    proc.stderr or "",
                ]
            ),
            encoding="utf-8",
        )
        await update.message.reply_text(
            f"Preview finished.\nreturncode={proc.returncode}\nlog={log_path.as_posix()}"
        )
    except Exception as exc:  # noqa: BLE001
        log_path.write_text(f"error={type(exc).__name__}: {exc}\n", encoding="utf-8")
        await update.message.reply_text(f"Preview failed: {type(exc).__name__}")


async def cmd_last_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    report = OUT_DIR / "GFIELD_V3_FULL_AUTO_FINAL_REPORT.txt"
    if not report.exists():
        await update.message.reply_text("No final report file yet.")
        return
    text = report.read_text(encoding="utf-8", errors="ignore")
    if len(text) > 3500:
        text = text[:3500] + "\n... (truncated)"
    await update.message.reply_text(text)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    raw = " ".join(context.args).strip() if context.args else ""
    name = _normalize_run_target(raw)
    if not name:
        await update.message.reply_text(
            "Usage: /run <target>\n"
            "Targets: 서버정보, 폴더목록, 전체상태"
        )
        return
    await _run_allowed_command(update, name)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.message.reply_text(
        "GFIELD commands\n"
        "/status\n"
        "/run_preview\n"
        "/last_report\n"
        "/run 서버정보\n"
        "/run 폴더목록\n"
        "/run 전체상태\n\n"
        "Chat style aliases:\n"
        "서버정보 | 폴더목록 | 전체상태"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    # Allow conversational use without /run.
    if text in ALIASES:
        await _run_allowed_command(update, ALIASES[text])
        return
    if text.startswith("/run "):
        parts = shlex.split(text)
        raw = " ".join(parts[1:]) if len(parts) > 1 else ""
        name = _normalize_run_target(raw)
        if name:
            await _run_allowed_command(update, name)
            return


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("run_preview", cmd_run_preview))
    app.add_handler(CommandHandler("last_report", cmd_last_report))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
