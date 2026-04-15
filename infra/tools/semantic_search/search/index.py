import os
import numpy as np
import pickle
import json
import fcntl
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
from .models import Chunk, SearchResult

class ForwardIndex:
    """儲存和管理 Chunks 及其 Embedding。使用 mmap 最佳化載入效能。"""
    
    def __init__(self, index_dir: Path, dim: int = 4096):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.embeddings_path = self.index_dir / "embeddings.npy"
        self.chunks_path = self.index_dir / "chunks.pkl"
        self.manifest_path = self.index_dir / "manifest.json"
        self.lock_path = self.index_dir / "index.lock"
        
        self.embeddings: Optional[np.ndarray] = None
        self.chunks: List[Chunk] = []
        self.manifest: Dict[str, Any] = {} # file_path -> {mtime, chunk_indices}
        
        self.load()

    def _get_lock(self, exclusive: bool = False):
        """獲取檔案鎖。"""
        mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        f = open(self.lock_path, 'w')
        fcntl.flock(f, mode)
        return f

    def load(self):
        """載入索引。使用 mmap 模式讀取向量。"""
        if not self.manifest_path.exists():
            return

        with self._get_lock(exclusive=False) as _:
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
            
            if self.chunks_path.exists():
                with open(self.chunks_path, 'rb') as f:
                    self.chunks = pickle.load(f)
            
            if self.embeddings_path.exists():
                # 使用 mmap 只讀模式載入，幾乎瞬時
                self.embeddings = np.load(self.embeddings_path, mmap_mode='r')

    def save(self, new_chunks: List[Chunk], updated_files: Dict[str, float]):
        """儲存/更新索引。需要排他鎖。"""
        with self._get_lock(exclusive=True) as _:
            # 1. 更新 chunks 列表
            # 注意：這只是一個簡單的實現。生產環境可能需要更精細的增量更新邏輯
            # 這裡我們假設 new_chunks 是要追加或替換的
            
            # 簡化的邏輯：先載入舊的，合併，再儲存
            # 如果索引很大，這種方式會變慢。但對於個人知識庫沒問題。
            all_chunks = self.chunks
            
            # 移除被更新檔案的舊 chunks
            all_chunks = [c for c in all_chunks if c.source_file not in updated_files]
            
            # 追加新 chunks
            start_idx = len(all_chunks)
            all_chunks.extend(new_chunks)
            
            # 更新 manifest
            for file_path, mtime in updated_files.items():
                indices = [i for i, c in enumerate(all_chunks) if c.source_file == file_path]
                self.manifest[file_path] = {
                    "mtime": mtime,
                    "indices": indices
                }
            
            self.chunks = all_chunks
            
            # 2. 儲存後設資料
            with open(self.chunks_path, 'wb') as f:
                pickle.dump(self.chunks, f)
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f)
                
            # 3. 儲存 Embeddings
            # 將所有 chunks 的 embedding 組合成一個大矩陣
            embeddings_list = [c.embedding for c in self.chunks]
            if embeddings_list:
                embeddings_array = np.array(embeddings_list, dtype=np.float32)
                np.save(self.embeddings_path, embeddings_array)
                # 重新載入為 mmap 模式
                self.embeddings = np.load(self.embeddings_path, mmap_mode='r')

    def get_subset(self, file_paths: List[str]) -> Tuple[List[Chunk], Optional[np.ndarray]]:
        """獲取指定檔案列表對應的子集。"""
        # 由於我們使用 mmap，可以直接透過索引訪問 self.embeddings
        target_chunks = []
        indices = []
        
        file_set = set(file_paths)
        for i, chunk in enumerate(self.chunks):
            if chunk.source_file in file_set:
                target_chunks.append(chunk)
                indices.append(i)
        
        if not indices or self.embeddings is None:
            return target_chunks, None
            
        subset_embeddings = self.embeddings[indices]
        return target_chunks, subset_embeddings

    def needs_update(self, file_path: str, current_mtime: float) -> bool:
        """檢查檔案是否需要更新特徵提取。"""
        record = self.manifest.get(file_path)
        if not record:
            return True
        return record.get("mtime") != current_mtime
