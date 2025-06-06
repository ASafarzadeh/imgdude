"""Tests for imgdude CLI."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from imgdude.cli import main


@pytest.fixture
def mock_uvicorn():
    """Mock uvicorn."""
    with patch("imgdude.cli.uvicorn") as mock_uvicorn:
        yield mock_uvicorn


@pytest.fixture
def mock_makedirs():
    """Mock os.makedirs."""
    with patch("os.makedirs") as mock_makedirs:
        yield mock_makedirs


def test_cli_default_arguments(mock_uvicorn, mock_makedirs):
    """CLI with default arguments."""
    # Save and restore environment variables
    original_env = os.environ.copy()
    
    try:
        # Clear relevant environment variables
        for var in ["IMGDUDE_MEDIA_ROOT", "IMGDUDE_CACHE_DIR", "IMGDUDE_CACHE_MAX_AGE", 
                    "IMGDUDE_MAX_WIDTH", "IMGDUDE_TRUSTED_HOSTS"]:
            if var in os.environ:
                del os.environ[var]
        
        # Mock sys.argv
        with patch("sys.argv", ["imgdude"]):
            main()
        
        # Check that uvicorn.run was called with default arguments
        mock_uvicorn.run.assert_called_once()
        args, kwargs = mock_uvicorn.run.call_args
        assert args[0] == "imgdude.main:app"
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 12312  # Updated default port
        assert kwargs["log_level"] == "info"
        
        # Check that environment variables were set
        assert os.environ["IMGDUDE_MEDIA_ROOT"] == "./media"
        assert os.environ["IMGDUDE_CACHE_DIR"] == "./cache"
        assert os.environ["IMGDUDE_CACHE_MAX_AGE"] == "604800"
        assert os.environ["IMGDUDE_MAX_WIDTH"] == "2000"
        assert os.environ["IMGDUDE_TRUSTED_HOSTS"] == ""  # Now defaults to empty string (allow all)
        
        # Check that directories were created
        mock_makedirs.assert_any_call("./media", exist_ok=True)
        mock_makedirs.assert_any_call("./cache", exist_ok=True)
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_cli_custom_arguments(mock_uvicorn, mock_makedirs):
    """CLI with custom arguments."""
    # Save and restore environment variables
    original_env = os.environ.copy()
    
    try:
        # Clear relevant environment variables
        for var in ["IMGDUDE_MEDIA_ROOT", "IMGDUDE_CACHE_DIR", "IMGDUDE_CACHE_MAX_AGE", 
                    "IMGDUDE_MAX_WIDTH", "IMGDUDE_TRUSTED_HOSTS", "IMGDUDE_IMAGE_WORKERS",
                    "IMGDUDE_IO_WORKERS", "IMGDUDE_MAX_CONNECTIONS", "IMGDUDE_WORKERS"]:
            if var in os.environ:
                del os.environ[var]
        
        # Mock sys.argv with custom arguments
        with patch("sys.argv", [
            "imgdude",
            "--host", "0.0.0.0",
            "--port", "9000",
            "--media-root", "/custom/media",
            "--cache-dir", "/custom/cache",
            "--cache-max-age", "3600",
            "--max-width", "1000",
            "--log-level", "debug",
            "--trusted-hosts", "192.168.1.1,10.0.0.1",
            "--image-workers", "8",
            "--io-workers", "4",
            "--max-connections", "200",
            "--workers", "4"
        ]):
            main()
        
        # Check that uvicorn.run was called with custom arguments
        mock_uvicorn.run.assert_called_once()
        args, kwargs = mock_uvicorn.run.call_args
        assert args[0] == "imgdude.main:app"
        assert kwargs["host"] == "0.0.0.0"
        assert kwargs["port"] == 9000
        assert kwargs["log_level"] == "debug"
        assert kwargs["workers"] == 4
        
        # Check that environment variables were set
        assert os.environ["IMGDUDE_MEDIA_ROOT"] == "/custom/media"
        assert os.environ["IMGDUDE_CACHE_DIR"] == "/custom/cache"
        assert os.environ["IMGDUDE_CACHE_MAX_AGE"] == "3600"
        assert os.environ["IMGDUDE_MAX_WIDTH"] == "1000"
        assert os.environ["IMGDUDE_TRUSTED_HOSTS"] == "192.168.1.1,10.0.0.1"
        assert os.environ["IMGDUDE_IMAGE_WORKERS"] == "8"
        assert os.environ["IMGDUDE_IO_WORKERS"] == "4"
        assert os.environ["IMGDUDE_MAX_CONNECTIONS"] == "200"
        
        # Check that directories were created
        mock_makedirs.assert_any_call("/custom/media", exist_ok=True)
        mock_makedirs.assert_any_call("/custom/cache", exist_ok=True)
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_cli_environment_variables(mock_uvicorn, mock_makedirs):
    """CLI respects environment variables."""
    # Save and restore environment variables
    original_env = os.environ.copy()
    
    try:
        # Set environment variables
        os.environ["IMGDUDE_MEDIA_ROOT"] = "/env/media"
        os.environ["IMGDUDE_CACHE_DIR"] = "/env/cache"
        os.environ["IMGDUDE_CACHE_MAX_AGE"] = "7200"
        os.environ["IMGDUDE_MAX_WIDTH"] = "1500"
        os.environ["IMGDUDE_TRUSTED_HOSTS"] = "10.0.0.5,172.16.0.1"
        
        # Mock sys.argv with minimal arguments
        with patch("sys.argv", ["imgdude"]):
            main()
        
        # Check that uvicorn.run was called
        mock_uvicorn.run.assert_called_once()
        
        # Check that environment variables were respected
        mock_makedirs.assert_any_call("/env/media", exist_ok=True)
        mock_makedirs.assert_any_call("/env/cache", exist_ok=True)
        
        # Check that the environment variables were preserved
        assert os.environ["IMGDUDE_MEDIA_ROOT"] == "/env/media"
        assert os.environ["IMGDUDE_CACHE_DIR"] == "/env/cache"
        assert os.environ["IMGDUDE_CACHE_MAX_AGE"] == "7200"
        assert os.environ["IMGDUDE_MAX_WIDTH"] == "1500"
        assert os.environ["IMGDUDE_TRUSTED_HOSTS"] == "10.0.0.5,172.16.0.1"
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_cli_directory_creation_error():
    """Directory creation error handling."""
    # Save and restore environment variables
    original_env = os.environ.copy()
    
    try:
        # We need to mock sys.exit early to intercept the exit
        with patch("sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit("Exit called")  # Make exit raise an exception to prevent code execution after
            
            # Then mock uvicorn
            with patch("imgdude.cli.uvicorn") as mock_uvicorn:
                # And finally mock os.makedirs to trigger the error path
                with patch("os.makedirs") as mock_makedirs:
                    mock_makedirs.side_effect = PermissionError("Permission denied")
                    
                    # Run with mocked argv
                    with patch("sys.argv", ["imgdude"]):
                        try:
                            main()
                        except SystemExit:
                            # Expected to exit, so we just pass
                            pass
                    
                    # Check that sys.exit was called with error code 1
                    mock_exit.assert_called_once_with(1)
                    
                    # uvicorn.run should not be called since we exit before that
                    mock_uvicorn.run.assert_not_called()
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env) 