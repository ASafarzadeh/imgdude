"""Cache management for imgdude."""

import os
import time
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Union, List, Set, Optional, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict

logger = logging.getLogger("imgdude.cache")

class CacheManager:
    """Handles image cache operations and cleanup."""
    def __init__(self, cache_dir: str, max_age_seconds: int = 604800, max_size_mb: int = 1024):
        """Initialize the cache manager.
        Args:
            cache_dir: Directory to store cached images
            max_age_seconds: Maximum age of cached files in seconds
            max_size_mb: Maximum size of cache in MB
        """
        self.cache_dir = Path(cache_dir)
        self.max_age_seconds = max_age_seconds
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self._thread_pool = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="cache_worker"
        )
        self._recently_accessed: OrderedDict[str, None] = OrderedDict()
        self._max_recently_accessed = 1000
        self._cleanup_lock = asyncio.Lock()

    def mark_accessed(self, file_path: str) -> None:
        """Mark a file as recently accessed to help prioritize cache cleanup."""
        if file_path in self._recently_accessed:
            del self._recently_accessed[file_path]
        
        self._recently_accessed[file_path] = None
        
        while len(self._recently_accessed) > self._max_recently_accessed:
            self._recently_accessed.popitem(last=False)

    async def clean_cache(self) -> Dict[str, Union[int, str, float]]:
        """Remove expired or excess items from the cache. Returns cleanup statistics."""
        async with self._cleanup_lock:
            try:
                logger.info("Starting cache cleanup")
                start_time = time.time()
                now = time.time()
                count = 0
                failed = 0
                removed_size = 0
                total_size = await self._get_cache_size()
                
                expired_stats = await self._clean_expired_files(now, total_size)
                count += expired_stats["removed"]
                failed += expired_stats["failed"]
                removed_size += expired_stats["removed_size"]
                total_size = expired_stats["new_total_size"]
                
                if total_size > self.max_size_bytes:
                    size_cleanup_stats = await self._clean_by_size(total_size)
                    count += size_cleanup_stats["removed"]
                    failed += size_cleanup_stats["failed"]
                    removed_size += size_cleanup_stats["removed_size"]
                    total_size = size_cleanup_stats["new_total_size"]
                
                process_time = time.time() - start_time
                logger.info(f"Cache cleanup complete: removed {count} files ({removed_size / (1024*1024):.2f} MB) in {process_time:.2f}s")
                return {
                    "removed_files": count,
                    "failed_files": failed,
                    "removed_size_bytes": removed_size,
                    "removed_size_mb": round(removed_size / (1024 * 1024), 2),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "max_size_mb": self.max_size_bytes // (1024 * 1024),
                    "process_time_seconds": round(process_time, 2)
                }
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")
                return {
                    "error": str(e),
                    "removed_files": 0,
                    "failed_files": 0
                }
    
    async def _clean_expired_files(self, now: float, total_size: int) -> Dict[str, Union[int, float]]:
        """Clean expired files from the cache."""
        count = 0
        failed = 0
        removed_size = 0
        
        for file_path in self.cache_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            try:
                mtime = os.path.getmtime(file_path)
                file_age = now - mtime
                
                if file_age > self.max_age_seconds:
                    file_size = file_path.stat().st_size
                    path_str = str(file_path)
                    is_recently_accessed = path_str in self._recently_accessed
                    
                    if is_recently_accessed and total_size < (self.max_size_bytes * 0.9):
                        continue
                        
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self._thread_pool, os.remove, file_path)
                    count += 1
                    removed_size += file_size
                    total_size -= file_size
                    
                    if path_str in self._recently_accessed:
                        del self._recently_accessed[path_str]
            except OSError as e:
                logger.error(f"Error accessing/removing file {file_path}: {str(e)}")
                failed += 1
        
        return {
            "removed": count,
            "failed": failed,
            "removed_size": removed_size,
            "new_total_size": total_size
        }
    
    async def _clean_by_size(self, total_size: int) -> Dict[str, Union[int, float]]:
        """Clean files based on size limits, starting with the oldest."""
        count = 0
        failed = 0
        removed_size = 0
        
        files_info = []
        
        for file_path in self.cache_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            try:
                path_str = str(file_path)
                mtime = os.path.getmtime(file_path)
                size = file_path.stat().st_size
                is_recently_accessed = path_str in self._recently_accessed
                
                files_info.append({
                    "path": file_path,
                    "mtime": mtime,
                    "size": size,
                    "is_recently_accessed": is_recently_accessed
                })
            except OSError as e:
                logger.error(f"Error accessing file {file_path}: {str(e)}")
                failed += 1
        
        files_info.sort(key=lambda x: (x["is_recently_accessed"], -x["mtime"]))
        
        for file_info in files_info:
            if total_size <= self.max_size_bytes:
                break
                
            file_path = file_info["path"]
            file_size = file_info["size"]
            path_str = str(file_path)
            
            if file_info["is_recently_accessed"] and total_size < (self.max_size_bytes * 0.9):
                continue
                
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._thread_pool, os.remove, file_path)
                count += 1
                removed_size += file_size
                total_size -= file_size
                
                if path_str in self._recently_accessed:
                    del self._recently_accessed[path_str]
            except OSError as e:
                logger.error(f"Error removing cache file {file_path}: {str(e)}")
                failed += 1
        
        return {
            "removed": count,
            "failed": failed, 
            "removed_size": removed_size,
            "new_total_size": total_size
        }

    async def start_periodic_cleanup(self, interval_seconds: int = 3600) -> None:
        """Periodically clean the cache in the background."""
        try:
            while True:
                await self.clean_cache()
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Periodic cache cleanup task cancelled")
            self._thread_pool.shutdown(wait=False)
            raise
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {str(e)}")
            raise

    async def _get_cache_size(self) -> int:
        """Calculate the total size of the cache in bytes."""
        try:
            loop = asyncio.get_event_loop()
            total_size = await loop.run_in_executor(
                self._thread_pool, 
                lambda: sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
            )
            return total_size
        except Exception as e:
            logger.error(f"Error calculating cache size: {str(e)}")
            return 0

    async def get_cache_stats(self) -> Dict[str, Union[int, float, str, List[str]]]:
        """Return statistics about the cache, including file types and disk usage."""
        try:
            start_time = time.time()
            total_files = 0
            total_size = 0
            oldest_file_age = 0
            newest_file_age = float('inf')
            now = time.time()
            file_exts: Dict[str, int] = {}
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    total_files += 1
                    size = file_path.stat().st_size
                    total_size += size
                    ext = file_path.suffix.lower()
                    file_exts[ext] = file_exts.get(ext, 0) + 1
                    try:
                        file_age = now - os.path.getmtime(file_path)
                        oldest_file_age = max(oldest_file_age, file_age)
                        newest_file_age = min(newest_file_age, file_age)
                    except OSError:
                        pass
            disk_usage = self._get_disk_usage(self.cache_dir)
            extensions = [f"{ext}: {count}" for ext, count in file_exts.items()]
            process_time = time.time() - start_time
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": str(self.cache_dir),
                "max_age_seconds": self.max_age_seconds,
                "max_size_mb": self.max_size_bytes // (1024 * 1024),
                "oldest_file_age_hours": round(oldest_file_age / 3600, 1) if oldest_file_age > 0 else 0,
                "newest_file_age_hours": round(newest_file_age / 3600, 1) if newest_file_age < float('inf') else 0,
                "file_types": extensions,
                "disk_usage": disk_usage,
                "process_time_seconds": round(process_time, 3)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "error": str(e),
                "total_files": 0,
                "total_size_bytes": 0
            }

    def _get_disk_usage(self, path: Path) -> Dict[str, Union[int, float]]:
        """Get disk usage information for the given path."""
        try:
            usage = shutil.disk_usage(path)
            return {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": round((usage.used / usage.total) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {str(e)}")
            return {
                "error": str(e)
            } 