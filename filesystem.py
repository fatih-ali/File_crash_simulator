import json
import time
import os
import hashlib
from typing import List, Dict, Optional
from disk import VirtualDisk

class FileSystem:
    """
    FileSystem manages files on top of a VirtualDisk.
    It uses an inode table to map filenames to blocks and maintains a write-ahead journal.
    """
    def __init__(self, disk: VirtualDisk, journal_path: str = "journal.log"):
        self.disk = disk
        self.journal_path = journal_path
        # Inode table maps filename to metadata
        # e.g., "file.txt": {"size": 100, "blocks": [1, 2], "created_at": "...", "checksum": "..."}
        self.inodes: Dict[str, dict] = {}
        
        # Create journal file if it doesn't exist
        if not os.path.exists(self.journal_path):
            open(self.journal_path, 'w').close()

    def _log_journal(self, action: str, filename: str, content: str = "") -> None:
        """Appends an action to the write-ahead journal."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "filename": filename,
            "content": content # Only used for CREATE to allow full reconstruction
        }
        with open(self.journal_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def create_file(self, filename: str, content: str) -> None:
        """
        Creates a new file by splitting its content into blocks and writing to disk.
        Uses write-ahead logging.
        """
        if filename in self.inodes:
            raise FileExistsError(f"File '{filename}' already exists.")

        size = len(content)
        if size == 0:
            blocks_needed = 0
        else:
            blocks_needed = (size + self.disk.block_size - 1) // self.disk.block_size

        # 1. Log intent to journal
        self._log_journal("CREATE", filename, content)

        # 2. Allocate blocks
        allocated_blocks = []
        if blocks_needed > 0:
            allocated_blocks = self.disk.allocate_blocks(blocks_needed)

        # 3. Write data to blocks
        for i, block_idx in enumerate(allocated_blocks):
            start = i * self.disk.block_size
            end = start + self.disk.block_size
            chunk = content[start:end]
            self.disk.write_block(block_idx, chunk)

        # 4. Update Inode table
        file_checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
        self.inodes[filename] = {
            "size": size,
            "blocks": allocated_blocks,
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "checksum": file_checksum
        }

    def read_file(self, filename: str) -> str:
        """Reads a file's content from the disk using its inode."""
        if filename not in self.inodes:
            raise FileNotFoundError(f"File '{filename}' not found.")
        
        inode = self.inodes[filename]
        content = ""
        for block_idx in inode["blocks"]:
            content += self.disk.read_block(block_idx)
            
        return content

    def delete_file(self, filename: str) -> None:
        """Deletes a file, freeing its blocks and removing its inode."""
        if filename not in self.inodes:
            raise FileNotFoundError(f"File '{filename}' not found.")

        # 1. Log intent to journal
        self._log_journal("DELETE", filename)

        # 2. Free blocks
        inode = self.inodes[filename]
        for block_idx in inode["blocks"]:
            self.disk.free_block(block_idx)

        # 3. Remove inode
        del self.inodes[filename]

    def list_files(self) -> List[dict]:
        """Returns a list of all files and their metadata."""
        file_list = []
        for name, meta in self.inodes.items():
            entry = {"name": name}
            entry.update(meta)
            file_list.append(entry)
        return file_list
