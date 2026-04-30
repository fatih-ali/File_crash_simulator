import random
import time
import hashlib
from disk import VirtualDisk
from filesystem import FileSystem

class CrashSimulator:
    """
    Simulates various file system and disk crash scenarios to test recovery mechanisms.
    """
    def __init__(self, disk: VirtualDisk, fs: FileSystem):
        self.disk = disk
        self.fs = fs

    def crash_type_1_corrupt_blocks(self, n: int) -> list[int]:
        """
        Randomly corrupts 'n' used blocks by overwriting data but keeping old checksums.
        Returns the list of corrupted block indices.
        """
        used_indices = [i for i, block in enumerate(self.disk.blocks) if block["used"]]
        if not used_indices:
            return []
        
        # Corrupt up to 'n' blocks (or as many as are used)
        num_to_corrupt = min(n, len(used_indices))
        blocks_to_corrupt = random.sample(used_indices, num_to_corrupt)

        for idx in blocks_to_corrupt:
            # Overwrite data with garbage
            self.disk.blocks[idx]["data"] = "CORRUPTED_DATA_" + str(random.randint(1000, 9999))
            # IMPORTANT: Do not update checksum to ensure verification fails!

        return blocks_to_corrupt

    def crash_type_2_wipe_metadata(self) -> None:
        """
        Simulates a metadata loss by clearing the entire inode table in RAM.
        The actual disk blocks remain, but the filesystem forgets about them.
        """
        self.fs.inodes.clear()

    def crash_type_3_partial_write(self, filename: str, content: str) -> None:
        """
        Simulates an interrupted write (e.g., power loss).
        Writes only half of the required blocks, but creates a broken inode pointing to all of them.
        """
        if filename in self.fs.inodes:
            raise FileExistsError(f"File '{filename}' already exists.")

        size = len(content)
        if size == 0:
            return

        blocks_needed = (size + self.disk.block_size - 1) // self.disk.block_size
        
        # 1. Log intent to journal
        self.fs._log_journal("CREATE", filename, content)

        # 2. Allocate blocks
        allocated_blocks = self.disk.allocate_blocks(blocks_needed)

        # 3. Write only HALF the blocks
        half = max(1, blocks_needed // 2)
        for i in range(half):
            block_idx = allocated_blocks[i]
            start = i * self.disk.block_size
            end = start + self.disk.block_size
            chunk = content[start:end]
            self.disk.write_block(block_idx, chunk)
            
        # The remaining blocks in `allocated_blocks` are marked "used" but have no valid data.

        # 4. Create broken Inode table
        file_checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
        self.fs.inodes[filename] = {
            "size": size,
            "blocks": allocated_blocks, # Points to some blocks that were never written!
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "checksum": file_checksum
        }
