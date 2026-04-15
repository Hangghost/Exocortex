from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

@dataclass
class Chunk:
    id: str                    # "{source_file}:{chunk_index}"
    text: str                  # 分塊文字內容
    embedding: Optional[np.ndarray] = None  # float32 向量
    source_file: str = ""       # 原始檔相對路徑
    header: str = ""           # 所屬標題
    position: Tuple[int, int] = (0, 0)  # (start_line, end_line)
    metadata: Dict[str, Any] = None

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        if not include_embedding:
            d.pop('embedding')
        return d

@dataclass
class SearchResult:
    chunk: Chunk
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": float(self.score),
            "chunk": self.chunk.to_dict()
        }
