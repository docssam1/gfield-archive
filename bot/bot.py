from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shlex
import subprocess
import uuid
from typing import Final

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


BASE_DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR: Final[pathlib.Path] = BASE_DIR / "gfield_output"
LOG_DIR: Final[pathlib.Path] = OUT_DIR / "logs"
SCRIPTS_DIR: Final[pathlib.Path] = BASE_DIR / "scripts"
PC_BRIDGE_DIR: Final[pathlib.Path] = pathlib.Path(
    os.getenv("GFIELD_PC_BRIDGE_DIR", str(OUT_DIR / "pc_bridge"))
)
PC_QUEUE_DIR: Final[pathlib.Path] = PC_BRIDGE_DIR / "queue"
PC_DONE_DIR: Final[pathlib.Path] = PC_BRIDGE_DIR / "done"
PC_RESULT_DIR: Final[pathlib.Path] = PC_BRIDGE_DIR / "results"

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
    "상태": "full_status",
    "목록": "folder_list",
    "serverinfo": "server_info",
    "folders": "folder_list",
    "statusall": "full_status",
}

PC_ALLOWED_TASKS: Final[set[str]] = {"ping", "status"}


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


def _normalize_run_target(raw: str) -> str:
    target = raw.strip()
    if not target:
        return ""
    return ALIASES.get(target, target)


async def _run_allowed_command(update: Update, name: str) -> None:
    if name not in ALLOWED_CMDS:
        await update.message.reply_text(
            "알 수 없는 실행 대상입니다.\n"
            "사용 가능: 서버정보, 폴더목록, 전체상태"
        )
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"run_{name}_{ts}.log"

    cmd = ALLOWED_CMDS[name]
    await update.message.reply_text(f"실행 중: {name}")
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
            f"완료: {name}\nreturncode={proc.returncode}\nlog={log_path.as_posix()}\n\n{preview}"
        )
    except Exception as exc:  # noqa: BLE001
        log_path.write_text(f"error={type(exc).__name__}: {exc}\n", encoding="utf-8")
        await update.message.reply_text(f"실행 실패: {type(exc).__name__}")


def _ensure_pc_bridge_dirs() -> None:
    PC_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    PC_DONE_DIR.mkdir(parents=True, exist_ok=True)
    PC_RESULT_DIR.mkdir(parents=True, exist_ok=True)


def _latest_result() -> pathlib.Path | None:
    if not PC_RESULT_DIR.exists():
        return None
    files = sorted(
        [p for p in PC_RESULT_DIR.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


async def _enqueue_pc_task(update: Update, task: str) -> None:
    if task not in PC_ALLOWED_TASKS:
        await update.message.reply_text("허용되지 않은 PC 작업입니다.")
        return
    _ensure_pc_bridge_dirs()
    task_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": task_id,
        "task": task,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": "telegram",
        "mode": "allowlist_only",
    }
    path = PC_QUEUE_DIR / f"{task_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    await update.message.reply_text(
        f"학원 PC 작업 등록: {task}\n"
        f"id={task_id}\n"
        f"queue={path.as_posix()}\n"
        "처리 후 PC결과 또는 /pc_result 로 확인하세요."
    )


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
    await update.message.reply_text("미리보기 작업 실행 중...")
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
            f"미리보기 완료\nreturncode={proc.returncode}\nlog={log_path.as_posix()}"
        )
    except Exception as exc:  # noqa: BLE001
        log_path.write_text(f"error={type(exc).__name__}: {exc}\n", encoding="utf-8")
        await update.message.reply_text(f"미리보기 실패: {type(exc).__name__}")


async def cmd_last_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    report = OUT_DIR / "GFIELD_V3_FULL_AUTO_FINAL_REPORT.txt"
    if not report.exists():
        await update.message.reply_text("최종 보고서 파일이 아직 없습니다.")
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
        await update.message.reply_text("사용법: /run <서버정보|폴더목록|전체상태>")
        return
    await _run_allowed_command(update, name)


async def cmd_pc_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await _enqueue_pc_task(update, "ping")


async def cmd_pc_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await _enqueue_pc_task(update, "status")


async def cmd_pc_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    _ensure_pc_bridge_dirs()
    queued = sorted(p.name for p in PC_QUEUE_DIR.glob("*.json"))
    done = sorted(p.name for p in PC_DONE_DIR.glob("*.json"))
    await update.message.reply_text(
        f"pc_bridge={PC_BRIDGE_DIR.as_posix()}\n"
        f"queued={len(queued)}\n"
        f"done={len(done)}\n"
        f"latest_queued={queued[-3:] if queued else []}"
    )


async def cmd_pc_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    result = _latest_result()
    if result is None:
        await update.message.reply_text("PC 결과가 아직 없습니다.")
        return
    text = result.read_text(encoding="utf-8", errors="ignore")
    if len(text) > 3200:
        text = text[:3200] + "\n... (truncated)"
    await update.message.reply_text(f"latest_result={result.name}\n{text}")


async def cmd_help_ko(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.message.reply_text(
        "[GFIELD 관제 명령]\n"
        "상태 확인:\n"
        "- 상태\n"
        "- 전체상태\n"
        "- 서버정보\n"
        "- 폴더목록\n"
        "- 목록\n\n"
        "학원 PC 연결:\n"
        "- PC핑\n"
        "- PC상태\n"
        "- PC목록\n"
        "- PC결과\n\n"
        "슬래시 명령:\n"
        "- /status\n"
        "- /pc_ping\n"
        "- /pc_status\n"
        "- /pc_queue\n"
        "- /pc_result\n"
        "- /run 서버정보\n"
        "- /run 폴더목록\n"
        "- /run 전체상태\n\n"
        "정책:\n"
        "- 학원 PC에는 Telegram 토큰 저장 안 함\n"
        "- PC 명령은 ping/status allowlist만 허용\n"
        "- 파일 변경/삭제/전송 명령은 아직 금지"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    if text in ALIASES:
        await _run_allowed_command(update, ALIASES[text])
        return
    if text in {"PC핑", "pc핑", "피씨핑"}:
        await _enqueue_pc_task(update, "ping")
        return
    if text in {"PC상태", "pc상태", "피씨상태"}:
        await _enqueue_pc_task(update, "status")
        return
    if text in {"PC목록", "pc목록", "피씨목록"}:
        await cmd_pc_queue(update, context)
        return
    if text in {"PC결과", "pc결과", "피씨결과"}:
        await cmd_pc_result(update, context)
        return
    if text.startswith("/run "):
        parts = shlex.split(text)
        raw = " ".join(parts[1:]) if len(parts) > 1 else ""
        name = _normalize_run_target(raw)
        if name:
            await _run_allowed_command(update, name)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_help_ko))
    app.add_handler(CommandHandler("help", cmd_help_ko))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("run_preview", cmd_run_preview))
    app.add_handler(CommandHandler("last_report", cmd_last_report))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("pc_ping", cmd_pc_ping))
    app.add_handler(CommandHandler("pc_status", cmd_pc_status))
    app.add_handler(CommandHandler("pc_queue", cmd_pc_queue))
    app.add_handler(CommandHandler("pc_result", cmd_pc_result))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
