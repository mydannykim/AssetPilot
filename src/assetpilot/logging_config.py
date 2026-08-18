from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "assetpilot.log"
_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 3

_configured = False


def _log_uncaught_exception(exc_type: type[BaseException], exc_value: BaseException, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.getLogger("assetpilot").error("처리되지 않은 예외로 종료", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def configure_logging(level: int = logging.INFO) -> None:
    """`data/assetpilot.log`에 요청/재시도/에러를 타임스탬프와 함께 기록한다.

    launchd StandardOutPath/StandardErrorPath(snapshot.log 등)는 그대로 두고,
    그와 별도로 코드 내부에서 무슨 일이 언제 있었는지 추적하기 위한 용도다.
    launchd에서든 대화형 실행에서든 한 번만 설정되도록 모듈 전역 플래그로 막는다.
    """
    global _configured
    if _configured:
        return
    _configured = True

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(_LOG_PATH, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    logger = logging.getLogger("assetpilot")
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    sys.excepthook = _log_uncaught_exception
