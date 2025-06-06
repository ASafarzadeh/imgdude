"""Tests for imgdude cache."""

import os
import time
import pytest
import asyncio
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from imgdude.cache import CacheManager


@pytest.fixture
def cache_dir():
    """Temporary cache dir."""
    test_cache_dir = Path("test_cache_tmp")
    test_cache_dir.mkdir(exist_ok=True)
    yield test_cache_dir
    shutil.rmtree(test_cache_dir)


@pytest.fixture
def cache_manager(cache_dir):
    """Cache manager instance."""
    return CacheManager(str(cache_dir), max_age_seconds=60, max_size_mb=5)


@pytest.mark.asyncio
async def test_clean_cache_empty(cache_manager):
    """Empty cache cleanup."""
    result = await cache_manager.clean_cache()
    assert result["removed_files"] == 0
    assert result["failed_files"] == 0
    assert result["removed_size_bytes"] == 0
    assert "total_size_mb" in result
    assert "max_size_mb" in result
    assert result["max_size_mb"] == 5


@pytest.mark.asyncio
async def test_clean_cache_with_files(cache_manager, cache_dir):
    """Cache cleanup with files."""
    # Create some files in the cache directory
    file1 = cache_dir / "test1.jpg"
    file2 = cache_dir / "test2.jpg"
    
    # Create files with content
    file1.write_bytes(b"test data 1")
    file2.write_bytes(b"test data 2")
    
    # Set one file to be old (expired)
    old_time = time.time() - 120  # 2 minutes old (exceeds 60s max age)
    os.utime(file1, (old_time, old_time))
    
    result = await cache_manager.clean_cache()
    assert result["removed_files"] == 1
    assert result["failed_files"] == 0
    assert result["removed_size_bytes"] > 0
    
    # Verify only the old file was removed
    assert not file1.exists()
    assert file2.exists()


@pytest.mark.asyncio
async def test_mark_accessed(cache_manager, cache_dir):
    """mark_accessed works."""
    # Create a file
    file1 = cache_dir / "test1.jpg"
    file2 = cache_dir / "test2.jpg"
    
    # Create files with content
    file1.write_bytes(b"test data 1")
    file2.write_bytes(b"test data 2")
    
    # Set both files to be old (expired)
    old_time = time.time() - 120  # 2 minutes old (exceeds 60s max age)
    os.utime(file1, (old_time, old_time))
    os.utime(file2, (old_time, old_time))
    
    # Mark one file as recently accessed
    cache_manager.mark_accessed(str(file1))
    
    # Clean cache
    result = await cache_manager.clean_cache()
    
    # The recently accessed file should still exist (unless we're critically low on space)
    assert file1.exists()
    assert not file2.exists()


@pytest.mark.asyncio
async def test_get_cache_stats(cache_manager, cache_dir):
    """get_cache_stats works."""
    # Create some files of different types
    (cache_dir / "test1.jpg").write_bytes(b"jpeg data")
    (cache_dir / "test2.png").write_bytes(b"png data")
    (cache_dir / "test3.jpg").write_bytes(b"more jpeg data")
    
    stats = await cache_manager.get_cache_stats()
    
    assert stats["total_files"] == 3
    assert stats["total_size_bytes"] > 0
    assert ".jpg: 2" in stats["file_types"]
    assert ".png: 1" in stats["file_types"]
    assert stats["cache_dir"] == str(cache_dir)
    assert stats["max_age_seconds"] == 60
    assert stats["max_size_mb"] == 5
    assert "disk_usage" in stats
    assert "process_time_seconds" in stats


@pytest.mark.asyncio
async def test_size_based_cleanup(cache_dir):
    """Cleanup by size limit."""
    # Create a cache manager with a very small size limit
    cache_manager = CacheManager(str(cache_dir), max_age_seconds=3600, max_size_mb=0.01)  # 10KB
    
    # Create some files that exceed the limit
    for i in range(5):
        file_path = cache_dir / f"test{i}.dat"
        # Create a 3KB file
        file_path.write_bytes(b"x" * 3000)
    
    # Clean cache
    result = await cache_manager.clean_cache()
    
    # Should have removed some files to get under the limit
    assert result["removed_files"] > 0
    assert "total_size_mb" in result
    # The size should be at most the limit (might be exactly at the limit)
    assert result["total_size_mb"] <= 0.01


@pytest.mark.asyncio
async def test_start_periodic_cleanup(cache_manager, cache_dir):
    """Periodic cleanup task."""
    # Create some files
    file1 = cache_dir / "old.jpg"
    file1.write_bytes(b"old data")
    
    # Set the file to be old
    old_time = time.time() - 120  # 2 minutes old
    os.utime(file1, (old_time, old_time))
    
    # Start the periodic cleanup with a short interval
    cleanup_task = asyncio.create_task(
        cache_manager.start_periodic_cleanup(interval_seconds=1)
    )
    
    # Wait a short time for the cleanup to run
    await asyncio.sleep(1.5)
    
    # Cancel the task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Verify the old file was removed
    assert not file1.exists()


@pytest.mark.asyncio
async def test_cache_error_handling():
    """Cache manager error handling."""
    # Create a temporary cache dir for this test
    temp_dir = Path("test_error_handling")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Create a cache manager with the temporary directory
        cache_manager = CacheManager(str(temp_dir))
        
        # Patch glob to raise an exception during get_cache_stats
        with patch.object(Path, 'glob') as mock_glob:
            mock_glob.side_effect = PermissionError("Permission denied")
            
            # Test get_cache_stats with the mocked glob
            stats = await cache_manager.get_cache_stats()
            assert "error" in stats
            assert stats["total_files"] == 0
            
            # Test clean_cache with the mocked glob
            result = await cache_manager.clean_cache()
            assert "error" in result or result["removed_files"] == 0
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_disk_usage(cache_manager):
    """Disk usage info."""
    # Get disk usage
    stats = await cache_manager.get_cache_stats()
    
    # Verify disk usage data is present
    assert "disk_usage" in stats
    disk_usage = stats["disk_usage"]
    
    # Basic checks for disk usage fields
    assert "total_bytes" in disk_usage
    assert "used_bytes" in disk_usage
    assert "free_bytes" in disk_usage
    assert "percent_used" in disk_usage 