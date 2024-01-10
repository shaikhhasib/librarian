"""
Path info object.
"""

from pathlib import Path
from pydantic import BaseModel

from typing import Optional

class PathInfo(BaseModel):
    """
    Path information for a file. It is the responsibility of the
    various implementations of the store managers to return valid
    PathInfo objects, which then serialize themselves.
    """
    path: Path
    "Path being considered"
    filetype: str
    "File type at the path (e.g. png)"
    md5: str
    "MD5 sum of the file at the path"
    size: int
    "Size in bytes of the file at the path"
    obsid: Optional[int] = None