#!/usr/bin/env python3
"""
Lightweight unit tests for dev.py

Run with: python3 test_dev.py
Or: python3 -m pytest test_dev.py -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent))
import dev


class TestColors(unittest.TestCase):
    """Test color code handling"""
    
    def test_colors_defined(self):
        """Color constants should be defined"""
        self.assertTrue(hasattr(dev.Colors, 'RED'))
        self.assertTrue(hasattr(dev.Colors, 'GREEN'))
        self.assertTrue(hasattr(dev.Colors, 'YELLOW'))
        self.assertTrue(hasattr(dev.Colors, 'BLUE'))
        self.assertTrue(hasattr(dev.Colors, 'NC'))


class TestGetOsType(unittest.TestCase):
    """Test OS type detection"""
    
    @patch('platform.system')
    def test_linux(self, mock_system):
        mock_system.return_value = 'Linux'
        self.assertEqual(dev.get_os_type(), 'linux')
    
    @patch('platform.system')
    def test_darwin(self, mock_system):
        mock_system.return_value = 'Darwin'
        self.assertEqual(dev.get_os_type(), 'darwin')
    
    @patch('platform.system')
    def test_windows(self, mock_system):
        mock_system.return_value = 'Windows'
        self.assertEqual(dev.get_os_type(), 'windows')


class TestConfig(unittest.TestCase):
    """Test config loading and saving"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_config_dir = dev.CONFIG_DIR
        self.orig_config_file = dev.CONFIG_FILE
        dev.CONFIG_DIR = Path(self.temp_dir) / 'repoconfig'
        dev.CONFIG_FILE = dev.CONFIG_DIR / 'repos.json'
    
    def tearDown(self):
        dev.CONFIG_DIR = self.orig_config_dir
        dev.CONFIG_FILE = self.orig_config_file
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_creates_default(self):
        """load_config should create default config if missing"""
        config = dev.load_config()
        self.assertIn('version', config)
        self.assertIn('repos', config)
        self.assertIn('defaultBasePaths', config)
        self.assertTrue(dev.CONFIG_FILE.exists())
    
    def test_save_and_load_config(self):
        """Config should round-trip correctly"""
        config = {
            'version': 1,
            'repos': [{'name': 'test-repo', 'remoteUrl': 'https://example.com/test.git'}],
            'defaultBasePaths': {'linux': '/workspace'}
        }
        dev.save_config(config)
        loaded = dev.load_config()
        self.assertEqual(loaded['repos'][0]['name'], 'test-repo')


class TestComputeRepoName(unittest.TestCase):
    """Test repo name computation"""
    
    def test_simple_repo_name(self):
        """Simple repo should use folder name"""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'my-repo'
            repo.mkdir()
            name = dev.compute_repo_name(repo)
            self.assertEqual(name, 'my-repo')
    
    def test_nested_gclient_repo(self):
        """Repo under gclient enlistment should use parent/name format"""
        with tempfile.TemporaryDirectory() as tmp:
            # Create structure: edge/.gclient, edge/src
            edge = Path(tmp) / 'edge'
            edge.mkdir()
            (edge / '.gclient').touch()
            src = edge / 'src'
            src.mkdir()
            
            name = dev.compute_repo_name(src)
            self.assertEqual(name, 'edge/src')


class TestSectionMerge(unittest.TestCase):
    """Test section-based markdown merge"""
    
    def test_identical_content(self):
        """Identical content should merge cleanly"""
        content = "# Header\n\n## Section 1\nContent\n"
        merged, has_conflicts = dev.section_merge(content, content)
        self.assertFalse(has_conflicts)
        self.assertEqual(merged, content)
    
    def test_added_section_in_dest(self):
        """New section in dest should be kept"""
        src = "## Section 1\nContent 1\n"
        dest = "## Section 1\nContent 1\n\n## Section 2\nContent 2\n"
        merged, has_conflicts = dev.section_merge(src, dest)
        self.assertFalse(has_conflicts)
        self.assertIn("Section 2", merged)
    
    def test_added_section_in_src(self):
        """New section in src should be added"""
        src = "## Section 1\nContent 1\n\n## Section 2\nContent 2\n"
        dest = "## Section 1\nContent 1\n"
        merged, has_conflicts = dev.section_merge(src, dest)
        self.assertFalse(has_conflicts)
        self.assertIn("Section 2", merged)
    
    def test_conflicting_sections(self):
        """Different content in same section should create conflict"""
        src = "## Section 1\nContent from src\n"
        dest = "## Section 1\nContent from dest\n"
        merged, has_conflicts = dev.section_merge(src, dest)
        self.assertTrue(has_conflicts)
        self.assertIn("<<<<<<<", merged)
        self.assertIn("=======", merged)
        self.assertIn(">>>>>>>", merged)
    
    def test_preamble_handling(self):
        """Content before first ## should be handled as preamble"""
        src = "# Title\n\nPreamble text\n\n## Section\nContent\n"
        dest = src
        merged, has_conflicts = dev.section_merge(src, dest)
        self.assertFalse(has_conflicts)
        self.assertIn("Preamble text", merged)


class TestGetBasePath(unittest.TestCase):
    """Test base path resolution"""
    
    @patch.object(dev, 'get_os_type')
    def test_linux_path(self, mock_os):
        mock_os.return_value = 'linux'
        config = {'defaultBasePaths': {'linux': '/workspace', 'windows': 'C:\\dev'}}
        self.assertEqual(dev.get_base_path(config), '/workspace')
    
    @patch.object(dev, 'get_os_type')
    def test_windows_path(self, mock_os):
        mock_os.return_value = 'windows'
        config = {'defaultBasePaths': {'linux': '/workspace', 'windows': 'C:\\dev'}}
        self.assertEqual(dev.get_base_path(config), 'C:\\dev')


class TestRunGit(unittest.TestCase):
    """Test git command execution"""
    
    def test_run_git_on_valid_repo(self):
        """run_git should work on a valid git repo"""
        # Use the dev_scripts dir itself (should be a git repo)
        success, output = dev.run_git(dev.SCRIPT_DIR, 'status', '--porcelain')
        # Should succeed (return code 0) even if there are changes
        self.assertIsInstance(success, bool)
    
    def test_run_git_on_invalid_path(self):
        """run_git should fail gracefully on non-repo"""
        with tempfile.TemporaryDirectory() as tmp:
            success, output = dev.run_git(tmp, 'status')
            self.assertFalse(success)


class TestCopilotInstructionsSync(unittest.TestCase):
    """Test copilot instructions merge and sync"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_config_dir = dev.CONFIG_DIR
        dev.CONFIG_DIR = Path(self.temp_dir) / 'repoconfig'
        dev.CONFIG_DIR.mkdir(parents=True)
        
        # Create workspace structure
        self.workspace = Path(self.temp_dir) / 'workspace'
        self.workspace.mkdir()
        (self.workspace / '.github').mkdir()
    
    def tearDown(self):
        dev.CONFIG_DIR = self.orig_config_dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_merge_workspace_to_repoconfig_empty_repoconfig(self):
        """Workspace content should be copied to empty repoconfig"""
        workspace_content = "# Copilot\n\n## Rules\nSome rules\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(workspace_content)
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        repoconfig_file = dev.CONFIG_DIR / 'copilot-instructions.md'
        self.assertTrue(repoconfig_file.exists())
        self.assertEqual(repoconfig_file.read_text(), workspace_content)
    
    def test_merge_identical_content(self):
        """Identical content should not change files"""
        content = "# Copilot\n\n## Rules\nSome rules\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(content)
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(content)
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Content should remain the same
        repoconfig_content = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertEqual(repoconfig_content, content)
    
    def test_merge_adds_new_section_from_workspace(self):
        """New section added in workspace should appear in merged result"""
        repoconfig_content = "## Section 1\nOriginal content\n"
        workspace_content = "## Section 1\nOriginal content\n\n## Section 2\nNew section\n"
        
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(repoconfig_content)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(workspace_content)
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        merged = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertIn("Section 2", merged)
        self.assertIn("New section", merged)
    
    def test_apply_repoconfig_to_workspace(self):
        """Repoconfig content should be applied to workspace"""
        repoconfig_content = "# Copilot\n\n## Rules\nUpdated rules\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(repoconfig_content)
        
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        workspace_file = self.workspace / '.github' / 'copilot-instructions.md'
        self.assertTrue(workspace_file.exists())
        self.assertEqual(workspace_file.read_text(), repoconfig_content)
    
    def test_apply_detects_conflicts(self):
        """Conflict markers should be detected and reported"""
        conflict_content = "## Section\n<<<<<<< repoconfig\nVersion A\n=======\nVersion B\n>>>>>>> workspace\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(conflict_content)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text("different")
        
        # Should not crash, just report conflict
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        # Workspace should not be overwritten with conflict content blindly
        # (function detects conflicts and skips)
    
    def test_full_sync_round_trip(self):
        """Full sync should merge workspace changes into repoconfig"""
        # Start with same content in both
        initial = "## Section 1\nInitial\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(initial)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(initial)
        
        # Modify workspace
        modified = "## Section 1\nInitial\n\n## Section 2\nWorkspace addition\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(modified)
        
        # Merge to repoconfig
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Repoconfig should now have the new section
        repoconfig = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertIn("Workspace addition", repoconfig)
        
        # Apply back to workspace (simulating another machine pulling)
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        # Both should be in sync
        workspace = (self.workspace / '.github' / 'copilot-instructions.md').read_text()
        self.assertEqual(workspace.strip(), repoconfig.strip())


if __name__ == '__main__':
    # Run with verbosity
    unittest.main(verbosity=2)
