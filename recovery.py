import json
import os
from disk import VirtualDisk
from filesystem import FileSystem

class RecoveryEngine:
    """
    Provides tools to detect corruption, repair damaged files, and restore 
    filesystem state from backups or journals.
    """
    def __init__(self, disk: VirtualDisk, fs: FileSystem):
        self.disk = disk
        self.fs = fs

    def scan_disk(self) -> list[int]:
        """
        Scans all blocks on the disk and verifies their checksums.
        Returns a list of corrupted block indices.
        """
        corrupted = []
        for i in range(self.disk.num_blocks):
            if not self.disk.verify_block(i):
                corrupted.append(i)
        return corrupted

    def recover_from_backup(self, backup_path: str = "backup_disk.json") -> None:
        """
        Reloads the entire disk state from a JSON backup.
        """
        self.disk.load_from_json(backup_path)

    def recover_from_journal(self) -> None:
        """
        Replays the journal to reconstruct the state.
        This will clear current inodes and disk, and replay all logged actions.
        """
        if not os.path.exists(self.fs.journal_path):
            return

        # Read journal
        entries = []
        with open(self.fs.journal_path, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        # Reset current state
        self.fs.inodes.clear()
        for i in range(self.disk.num_blocks):
            self.disk.free_block(i)
            
        # We need to temporarily disable journal logging while replaying 
        # so we don't duplicate journal entries.
        original_journal = self.fs.journal_path
        self.fs.journal_path = "temp_journal.log"
        open(self.fs.journal_path, 'w').close()
        
        try:
            # Replay entries
            for entry in entries:
                action = entry["action"]
                filename = entry["filename"]
                
                if action == "CREATE":
                    content = entry.get("content", "")
                    try:
                        self.fs.create_file(filename, content)
                    except FileExistsError:
                        pass
                elif action == "DELETE":
                    try:
                        self.fs.delete_file(filename)
                    except FileNotFoundError:
                        pass
        finally:
            # Restore journal path
            if os.path.exists(self.fs.journal_path):
                os.remove(self.fs.journal_path)
            self.fs.journal_path = original_journal

    def reconstruct_metadata(self) -> list[str]:
        """
        Rebuilds the inode table from journal entries.
        Returns the list of recovered filenames.
        """
        self.recover_from_journal()
        return list(self.fs.inodes.keys())

    def repair_corrupted_blocks(self, corrupted_ids: list[int]) -> list[str]:
        """
        Frees bad blocks and marks affected files as damaged by renaming them.
        Returns a list of damaged filenames.
        """
        damaged_files = set()
        
        for name, inode in list(self.fs.inodes.items()):
            for block_idx in corrupted_ids:
                if block_idx in inode["blocks"]:
                    damaged_files.add(name)
                    break
                    
        # Apply changes
        for name in damaged_files:
            inode = self.fs.inodes.pop(name)
            self.fs.inodes[name + "_DAMAGED"] = inode

        # Free the actual corrupted blocks so they can be reused
        for idx in corrupted_ids:
            self.disk.free_block(idx)
            
        return list(damaged_files)
