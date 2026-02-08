
from datetime import datetime
import inspect
from typing import List
import os
from config import LOG_FILE, UVICORN_LOG_FILE


def log(*msg: str) -> None:
    """
    Logs messages to log.txt, prepending:
    - timestamp with milliseconds
    - file name
    - function name
    - line number
    """

    # Caller info (1 level up the stack)
    frame = inspect.stack()[1]
    file_name = os.path.basename(frame.filename)
    func_name = frame.function
    line_no = frame.lineno

    # Timestamp
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # Prefix
    prefix = (
        f"[{time_str}]\t"
        f"[{file_name} - {func_name}():{line_no}]\t\t"
    )

    # Write log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for m in msg:
            f.write(f"{prefix}{m}\n")
            
def log_uvicorn(msg: str) -> None:
    """
    Logs messages to log.txt, prepending uvicorn tag.
    """

    # Timestamp
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # Prefix
    prefix = f"[{time_str}]\t[uvicorn]\t\t"

    # Write log
    with open(UVICORN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{prefix}{msg}\n")
        
        
