"""Tests for configuration manager.

Tests persistent configuration handling including save/load, validation,
recent files/directories, and cross-platform compatibility.
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager()
        # Override config directory to use temp dir
        self.config_manager.config_dir = Path(self.test_dir)
        self.config_manager.config_file = Path(self.test_dir) / "config.json"

    def tearDown(self):
        """Clean up test environment."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_default_config(self):
        """Test default configuration values."""
        config = self.config_manager.load_config()

        self.assertEqual(config["last_input_file"], "")
        self.assertEqual(config["last_output_dir"], "")
        self.assertEqual(config["organization_option"], "none")
        self.assertTrue(config["generate_positive_summary"])
        self.assertEqual(config["window_geometry"]["width"], 1000)
        self.assertEqual(config["window_geometry"]["height"], 700)
        self.assertTrue(config["show_welcome"])

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        # Set custom values
        config = self.config_manager.load_config()
        config["last_input_file"] = "/path/to/file.csv"
        config["last_output_dir"] = "/path/to/output"
        config["organization_option"] = "collection-date"
        config["generate_positive_summary"] = False

        # Save
        result = self.config_manager.save_config(config)
        self.assertTrue(result)
        self.assertTrue(self.config_manager.config_file.exists())

        # Create new manager and load
        new_manager = ConfigManager()
        new_manager.config_dir = Path(self.test_dir)
        new_manager.config_file = Path(self.test_dir) / "config.json"
        loaded_config = new_manager.load_config()

        # Verify loaded values
        self.assertEqual(loaded_config["last_input_file"], "/path/to/file.csv")
        self.assertEqual(loaded_config["last_output_dir"], "/path/to/output")
        self.assertEqual(loaded_config["organization_option"], "collection-date")
        self.assertFalse(loaded_config["generate_positive_summary"])

    def test_get_set_methods(self):
        """Test get and set methods."""
        # Test get with default
        value = self.config_manager.get("nonexistent", "default_value")
        self.assertEqual(value, "default_value")

        # Test set
        self.config_manager.set("test_key", "test_value")
        value = self.config_manager.get("test_key")
        self.assertEqual(value, "test_value")

    def test_update_method(self):
        """Test update method for multiple values."""
        updates = {
            "last_input_file": "/new/file.csv",
            "last_output_dir": "/new/output",
            "organization_option": "mrn"
        }

        self.config_manager.update(updates)

        self.assertEqual(self.config_manager.get("last_input_file"), "/new/file.csv")
        self.assertEqual(self.config_manager.get("last_output_dir"), "/new/output")
        self.assertEqual(self.config_manager.get("organization_option"), "mrn")

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        # Modify config
        self.config_manager.set("last_input_file", "/path/to/file.csv")
        self.config_manager.set("organization_option", "tested-date")

        # Reset
        config = self.config_manager.reset_to_defaults()

        # Verify defaults restored
        self.assertEqual(config["last_input_file"], "")
        self.assertEqual(config["organization_option"], "none")
        self.assertTrue(config["generate_positive_summary"])

    def test_add_recent_file(self):
        """Test adding files to recent files list."""
        # Add files
        self.config_manager.add_recent_file("/path/to/file1.csv")
        self.config_manager.add_recent_file("/path/to/file2.csv")
        self.config_manager.add_recent_file("/path/to/file3.csv")

        recent = self.config_manager.get("recent_input_files")
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0], "/path/to/file3.csv")  # Most recent first
        self.assertEqual(recent[1], "/path/to/file2.csv")
        self.assertEqual(recent[2], "/path/to/file1.csv")

    def test_add_recent_file_duplicate(self):
        """Test adding duplicate file moves it to top."""
        # Add files
        self.config_manager.add_recent_file("/path/to/file1.csv")
        self.config_manager.add_recent_file("/path/to/file2.csv")
        self.config_manager.add_recent_file("/path/to/file1.csv")  # Duplicate

        recent = self.config_manager.get("recent_input_files")
        self.assertEqual(len(recent), 2)  # Should not duplicate
        self.assertEqual(recent[0], "/path/to/file1.csv")  # Moved to top
        self.assertEqual(recent[1], "/path/to/file2.csv")

    def test_add_recent_file_max_limit(self):
        """Test recent files list respects max limit."""
        # Add more than max items
        for i in range(15):
            self.config_manager.add_recent_file(f"/path/to/file{i}.csv")

        recent = self.config_manager.get("recent_input_files")
        max_items = self.config_manager.get("max_recent_items")

        # Should be limited to max
        self.assertEqual(len(recent), max_items)
        # Most recent should be first
        self.assertEqual(recent[0], "/path/to/file14.csv")

    def test_add_recent_dir(self):
        """Test adding directories to recent directories list."""
        # Add directories
        self.config_manager.add_recent_dir("/path/to/dir1")
        self.config_manager.add_recent_dir("/path/to/dir2")

        recent = self.config_manager.get("recent_output_dirs")
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0], "/path/to/dir2")  # Most recent first
        self.assertEqual(recent[1], "/path/to/dir1")

    def test_get_recent_files_filters_nonexistent(self):
        """Test get_recent_files returns only existing files."""
        # Add mix of existing and non-existing files
        # Create a real temp file
        temp_file = Path(self.test_dir) / "test.csv"
        temp_file.touch()

        self.config_manager.add_recent_file(str(temp_file))
        self.config_manager.add_recent_file("/nonexistent/file.csv")

        recent = self.config_manager.get_recent_files()

        # Should only return existing file
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], str(temp_file))

    def test_get_recent_dirs_filters_nonexistent(self):
        """Test get_recent_dirs returns only existing directories."""
        # Add mix of existing and non-existing dirs
        self.config_manager.add_recent_dir(self.test_dir)
        self.config_manager.add_recent_dir("/nonexistent/directory")

        recent = self.config_manager.get_recent_dirs()

        # Should only return existing directory
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], self.test_dir)

    def test_validate_organization_option(self):
        """Test validation of organization option."""
        config = self.config_manager.load_config()

        # Set invalid value
        config["organization_option"] = "invalid"
        validated = self.config_manager._validate_config(config)

        # Should be reset to default
        self.assertEqual(validated["organization_option"], "none")

    def test_validate_boolean_values(self):
        """Test validation of boolean configuration values."""
        config = self.config_manager.load_config()

        # Set invalid boolean values
        config["generate_positive_summary"] = "not_a_bool"
        config["show_welcome"] = 123

        validated = self.config_manager._validate_config(config)

        # Should be reset to defaults
        self.assertTrue(validated["generate_positive_summary"])
        self.assertTrue(validated["show_welcome"])

    def test_validate_window_geometry(self):
        """Test validation of window geometry."""
        config = self.config_manager.load_config()

        # Set invalid geometry
        config["window_geometry"] = "not_a_dict"

        validated = self.config_manager._validate_config(config)

        # Should be reset to default dict
        self.assertIsInstance(validated["window_geometry"], dict)
        self.assertIn("width", validated["window_geometry"])
        self.assertIn("height", validated["window_geometry"])

    def test_validate_recent_lists(self):
        """Test validation of recent files and directories lists."""
        config = self.config_manager.load_config()

        # Set invalid types
        config["recent_input_files"] = "not_a_list"
        config["recent_output_dirs"] = {"not": "a list"}

        validated = self.config_manager._validate_config(config)

        # Should be reset to empty lists
        self.assertEqual(validated["recent_input_files"], [])
        self.assertEqual(validated["recent_output_dirs"], [])

    def test_validate_recent_lists_with_non_string_items(self):
        """Test validation removes non-string items from recent lists."""
        config = self.config_manager.load_config()

        # Add mix of valid and invalid items
        config["recent_input_files"] = ["/valid/path.csv", 123, None, {"invalid": "dict"}]
        config["recent_output_dirs"] = ["/valid/dir", 456, [], "another/valid"]

        validated = self.config_manager._validate_config(config)

        # Should only keep string items
        self.assertEqual(validated["recent_input_files"], ["/valid/path.csv"])
        self.assertEqual(validated["recent_output_dirs"], ["/valid/dir", "another/valid"])

    def test_corrupted_config_file(self):
        """Test handling of corrupted configuration file."""
        # Create corrupted JSON file
        with open(self.config_manager.config_file, 'w') as f:
            f.write("{ invalid json")

        # Should load defaults without crashing
        config = self.config_manager.load_config()
        self.assertEqual(config["organization_option"], "none")
        self.assertTrue(config["generate_positive_summary"])

    def test_missing_config_file(self):
        """Test loading when config file doesn't exist."""
        # Config file doesn't exist yet
        self.assertFalse(self.config_manager.config_file.exists())

        # Should load defaults
        config = self.config_manager.load_config()
        self.assertEqual(config["organization_option"], "none")

    def test_ensure_config_dir(self):
        """Test ensuring configuration directory exists."""
        # Remove directory
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

        # Ensure directory
        result = self.config_manager.ensure_config_dir()
        self.assertTrue(result)
        self.assertTrue(self.config_manager.config_dir.exists())

    def test_get_config_path(self):
        """Test getting configuration file path."""
        path = self.config_manager.get_config_path()
        self.assertEqual(path, self.config_manager.config_file)

    def test_atomic_save(self):
        """Test atomic save with temp file."""
        config = self.config_manager.load_config()
        config["test_key"] = "test_value"

        # Save should use atomic write
        result = self.config_manager.save_config(config)
        self.assertTrue(result)

        # Temp file should not exist
        temp_file = self.config_manager.config_file.with_suffix('.json.tmp')
        self.assertFalse(temp_file.exists())

        # Config file should exist with correct content
        with open(self.config_manager.config_file, 'r') as f:
            loaded = json.load(f)
        self.assertEqual(loaded["test_key"], "test_value")

    def test_save_without_loaded_config(self):
        """Test saving when no config has been loaded."""
        result = self.config_manager.save_config()
        self.assertFalse(result)  # Should return False if nothing to save

    def test_multiple_load_calls(self):
        """Test that multiple load calls return cached config."""
        config1 = self.config_manager.load_config()
        config2 = self.config_manager.load_config()

        # Should be the same object (cached)
        self.assertIs(config1, config2)


if __name__ == '__main__':
    unittest.main()
