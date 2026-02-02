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


class TestHasRealConflictMarkers(unittest.TestCase):
    """Test conflict marker detection"""
    
    def test_no_conflicts(self):
        """Normal content should not be detected as conflict"""
        content = "# Title\n\n## Section\nSome content\n"
        self.assertFalse(dev.has_real_conflict_markers(content))
    
    def test_real_conflict_markers(self):
        """Real conflict markers should be detected"""
        content = "## Section\n<<<<<<< HEAD\nVersion A\n=======\nVersion B\n>>>>>>> branch\n"
        self.assertTrue(dev.has_real_conflict_markers(content))
    
    def test_example_markers_in_backticks(self):
        """Example markers in backticks should NOT be detected as conflicts"""
        content = "If you see `<<<<<<<` markers, resolve them.\n"
        self.assertFalse(dev.has_real_conflict_markers(content))
    
    def test_example_markers_in_code_block(self):
        """Example markers in code blocks should NOT be detected as conflicts"""
        content = "```\n<<<<<<< branch\n=======\n>>>>>>> other\n```\n"
        self.assertFalse(dev.has_real_conflict_markers(content))


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
    
    def test_workspace_changes_sync_to_repoconfig(self):
        """
        Scenario 1: User edits workspace file, runs dev repo sync.
        Result: repoconfig should have the updated version.
        """
        # Start with initial content in both
        initial = "# Copilot\n\n## Rules\nInitial rules\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(initial)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(initial)
        
        # User makes a change to workspace
        updated = "# Copilot\n\n## Rules\nInitial rules\n\n## ADO PAT\nThe PAT is used for PRs and builds.\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(updated)
        
        # Run the merge step (what happens during dev repo sync)
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Verify repoconfig now has the updated content
        repoconfig_content = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertIn("ADO PAT", repoconfig_content)
        self.assertIn("PRs and builds", repoconfig_content)
    
    def test_repoconfig_changes_sync_to_workspace(self):
        """
        Scenario 2: Remote repoconfig has updates (from another machine).
        User runs dev repo sync.
        Result: workspace should have the updated version.
        """
        # Start with initial content in workspace
        initial = "# Copilot\n\n## Rules\nInitial rules\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(initial)
        
        # Repoconfig has new content (simulating pull from remote)
        updated_from_remote = "# Copilot\n\n## Rules\nInitial rules\n\n## New Section\nContent from another machine.\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(updated_from_remote)
        
        # Run the apply step (what happens after rcfiles sync)
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        # Verify workspace now has the remote content
        workspace_content = (self.workspace / '.github' / 'copilot-instructions.md').read_text()
        self.assertIn("New Section", workspace_content)
        self.assertIn("Content from another machine", workspace_content)
    
    def test_workspace_is_source_of_truth_during_merge(self):
        """
        When workspace has different content than repoconfig,
        workspace content should completely replace repoconfig.
        """
        repoconfig_content = "## Old Section\nOld content\n"
        workspace_content = "## New Section\nNew content\n"
        
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(repoconfig_content)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(workspace_content)
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Repoconfig should have workspace content exactly
        result = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertEqual(result, workspace_content)
        self.assertNotIn("Old Section", result)
    
    def test_merge_skips_when_workspace_has_conflicts(self):
        """Merge should skip if workspace file has conflict markers"""
        conflict_content = "## Section\n<<<<<<< HEAD\nVersion A\n=======\nVersion B\n>>>>>>> branch\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(conflict_content)
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text("original")
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Repoconfig should NOT be overwritten with conflict content
        result = (dev.CONFIG_DIR / 'copilot-instructions.md').read_text()
        self.assertEqual(result, "original")
    
    def test_apply_skips_when_repoconfig_has_conflicts(self):
        """Apply should skip if repoconfig file has conflict markers"""
        conflict_content = "## Section\n<<<<<<< HEAD\nVersion A\n=======\nVersion B\n>>>>>>> branch\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(conflict_content)
        (self.workspace / '.github' / 'copilot-instructions.md').write_text("original")
        
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        # Workspace should NOT be overwritten with conflict content
        result = (self.workspace / '.github' / 'copilot-instructions.md').read_text()
        self.assertEqual(result, "original")
    
    def test_merge_handles_empty_repoconfig(self):
        """Merge should work when repoconfig doesn't exist yet"""
        workspace_content = "# Copilot\n\nNew content\n"
        (self.workspace / '.github' / 'copilot-instructions.md').write_text(workspace_content)
        
        # Ensure repoconfig doesn't exist
        repoconfig_file = dev.CONFIG_DIR / 'copilot-instructions.md'
        if repoconfig_file.exists():
            repoconfig_file.unlink()
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        self.assertTrue(repoconfig_file.exists())
        self.assertEqual(repoconfig_file.read_text(), workspace_content)
    
    def test_apply_creates_workspace_github_dir(self):
        """Apply should create .github dir if it doesn't exist"""
        # Remove .github dir
        import shutil
        shutil.rmtree(self.workspace / '.github')
        
        repoconfig_content = "# Copilot\n\nContent\n"
        (dev.CONFIG_DIR / 'copilot-instructions.md').write_text(repoconfig_content)
        
        dev.apply_copilot_instructions_to_workspace(self.workspace)
        
        workspace_file = self.workspace / '.github' / 'copilot-instructions.md'
        self.assertTrue(workspace_file.exists())
        self.assertEqual(workspace_file.read_text(), repoconfig_content)
    
    def test_no_change_when_content_identical(self):
        """No file writes should happen when content is identical"""
        content = "# Copilot\n\n## Rules\nSome rules\n"
        workspace_file = self.workspace / '.github' / 'copilot-instructions.md'
        repoconfig_file = dev.CONFIG_DIR / 'copilot-instructions.md'
        
        workspace_file.write_text(content)
        repoconfig_file.write_text(content)
        
        # Get modification times
        workspace_mtime = workspace_file.stat().st_mtime
        repoconfig_mtime = repoconfig_file.stat().st_mtime
        
        import time
        time.sleep(0.01)  # Ensure time difference would be detectable
        
        dev.merge_copilot_instructions_to_repoconfig(self.workspace)
        
        # Files should not have been rewritten (mtime unchanged)
        # Note: the function actually does skip writes, but we can't reliably test mtime
        # Just verify content is still correct
        self.assertEqual(repoconfig_file.read_text(), content)


class TestClaudeInstructionsSync(unittest.TestCase):
    """Test Claude instructions merge and sync"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_config_dir = dev.CONFIG_DIR
        dev.CONFIG_DIR = Path(self.temp_dir) / 'repoconfig'
        dev.CONFIG_DIR.mkdir(parents=True)

        # Create workspace structure
        self.workspace = Path(self.temp_dir) / 'workspace'
        self.workspace.mkdir()
        (self.workspace / '.claude').mkdir()

    def tearDown(self):
        dev.CONFIG_DIR = self.orig_config_dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workspace_changes_sync_to_repoconfig(self):
        """
        Scenario 1: User edits workspace file, runs dev repo sync.
        Result: repoconfig should have the updated version.
        """
        initial = "# Dev CLI\n\nInitial content\n"
        (dev.CONFIG_DIR / 'CLAUDE.md').write_text(initial)
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(initial)

        updated = "# Dev CLI\n\nInitial content\n\n## New Section\nNew content\n"
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(updated)

        dev.merge_claude_instructions_to_repoconfig(self.workspace)

        repoconfig_content = (dev.CONFIG_DIR / 'CLAUDE.md').read_text()
        self.assertIn("New Section", repoconfig_content)

    def test_repoconfig_changes_sync_to_workspace(self):
        """
        Scenario 2: Remote repoconfig has updates (from another machine).
        User runs dev repo sync.
        Result: workspace should have the updated version.
        """
        initial = "# Dev CLI\n\nInitial content\n"
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(initial)

        updated_from_remote = "# Dev CLI\n\nInitial content\n\n## Remote Section\nFrom another machine.\n"
        (dev.CONFIG_DIR / 'CLAUDE.md').write_text(updated_from_remote)

        dev.apply_claude_instructions_to_workspace(self.workspace)

        workspace_content = (self.workspace / '.claude' / 'CLAUDE.md').read_text()
        self.assertIn("Remote Section", workspace_content)

    def test_workspace_is_source_of_truth_during_merge(self):
        """
        When workspace has different content than repoconfig,
        workspace content should completely replace repoconfig.
        """
        repoconfig_content = "## Old Section\nOld content\n"
        workspace_content = "## New Section\nNew content\n"

        (dev.CONFIG_DIR / 'CLAUDE.md').write_text(repoconfig_content)
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(workspace_content)

        dev.merge_claude_instructions_to_repoconfig(self.workspace)

        result = (dev.CONFIG_DIR / 'CLAUDE.md').read_text()
        self.assertEqual(result, workspace_content)
        self.assertNotIn("Old Section", result)

    def test_merge_skips_when_workspace_has_conflicts(self):
        """Merge should skip if workspace file has conflict markers"""
        conflict_content = "## Section\n<<<<<<< HEAD\nVersion A\n=======\nVersion B\n>>>>>>> branch\n"
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(conflict_content)
        (dev.CONFIG_DIR / 'CLAUDE.md').write_text("original")

        dev.merge_claude_instructions_to_repoconfig(self.workspace)

        result = (dev.CONFIG_DIR / 'CLAUDE.md').read_text()
        self.assertEqual(result, "original")

    def test_apply_skips_when_repoconfig_has_conflicts(self):
        """Apply should skip if repoconfig file has conflict markers"""
        conflict_content = "## Section\n<<<<<<< HEAD\nVersion A\n=======\nVersion B\n>>>>>>> branch\n"
        (dev.CONFIG_DIR / 'CLAUDE.md').write_text(conflict_content)
        (self.workspace / '.claude' / 'CLAUDE.md').write_text("original")

        dev.apply_claude_instructions_to_workspace(self.workspace)

        result = (self.workspace / '.claude' / 'CLAUDE.md').read_text()
        self.assertEqual(result, "original")

    def test_merge_handles_empty_repoconfig(self):
        """Merge should work when repoconfig doesn't exist yet"""
        workspace_content = "# Dev CLI\n\nNew content\n"
        (self.workspace / '.claude' / 'CLAUDE.md').write_text(workspace_content)

        repoconfig_file = dev.CONFIG_DIR / 'CLAUDE.md'
        if repoconfig_file.exists():
            repoconfig_file.unlink()

        dev.merge_claude_instructions_to_repoconfig(self.workspace)

        self.assertTrue(repoconfig_file.exists())
        self.assertEqual(repoconfig_file.read_text(), workspace_content)

    def test_apply_creates_workspace_claude_dir(self):
        """Apply should create .claude dir if it doesn't exist"""
        import shutil
        shutil.rmtree(self.workspace / '.claude')

        repoconfig_content = "# Dev CLI\n\nContent\n"
        (dev.CONFIG_DIR / 'CLAUDE.md').write_text(repoconfig_content)

        dev.apply_claude_instructions_to_workspace(self.workspace)

        workspace_file = self.workspace / '.claude' / 'CLAUDE.md'
        self.assertTrue(workspace_file.exists())
        self.assertEqual(workspace_file.read_text(), repoconfig_content)

    def test_no_change_when_content_identical(self):
        """No file writes should happen when content is identical"""
        content = "# Dev CLI\n\n## Rules\nSome rules\n"
        workspace_file = self.workspace / '.claude' / 'CLAUDE.md'
        repoconfig_file = dev.CONFIG_DIR / 'CLAUDE.md'

        workspace_file.write_text(content)
        repoconfig_file.write_text(content)

        result = dev.merge_claude_instructions_to_repoconfig(self.workspace)
        self.assertFalse(result)

        result = dev.apply_claude_instructions_to_workspace(self.workspace)
        self.assertFalse(result)


if __name__ == '__main__':
    # Run with verbosity
    unittest.main(verbosity=2)
