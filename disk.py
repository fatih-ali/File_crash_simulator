import json
import hashlib
from typing import List, Dict

class VirtualDisk:
    """
    VirtualDisk simulates a basic physical disk with a fixed number of blocks.
    Each block has a fixed size and stores data, a used flag, and an MD5 checksum.
    """
    def __init__(self, num_blocks: int = 32, block_size: int = 64):
        self.num_blocks = num_blocks
        self.block_size = block_size
        # Initialize blocks as a list of dictionaries
        self.blocks = []
        for _ in range(num_blocks):
            self.blocks.append({"data": "", "used": False, "checksum": ""})

    def _compute_checksum(self, data: str) -> str:
        """Computes the MD5 checksum of a given string."""
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def allocate_blocks(self, count: int) -> List[int]:
        """
        Finds 'count' free blocks and returns their indices.
        Raises an exception if not enough space.
        """
        free_indices = [i for i, block in enumerate(self.blocks) if not block["used"]]
        if len(free_indices) < count:
            raise MemoryError(f"Not enough free space. Need {count} blocks, but only {len(free_indices)} available.")
        
        # Mark them as used so they aren't double-allocated in quick succession
        allocated = free_indices[:count]
        for idx in allocated:
            self.blocks[idx]["used"] = True
            
        return allocated

    def write_block(self, index: int, data: str) -> None:
        """Writes data to a specific block and updates its checksum."""
        if index < 0 or index >= self.num_blocks:
            raise IndexError("Block index out of bounds.")
        
        # Store up to block_size characters
        block_data = data[:self.block_size] 
        self.blocks[index]["data"] = block_data
        self.blocks[index]["used"] = True
        self.blocks[index]["checksum"] = self._compute_checksum(block_data)

    def read_block(self, index: int) -> str:
        """Reads data from a specific block."""
        if index < 0 or index >= self.num_blocks:
            raise IndexError("Block index out of bounds.")
        return self.blocks[index]["data"]

    def free_block(self, index: int) -> None:
        """Frees a specific block."""
        if index < 0 or index >= self.num_blocks:
            raise IndexError("Block index out of bounds.")
        self.blocks[index]["data"] = ""
        self.blocks[index]["used"] = False
        self.blocks[index]["checksum"] = ""

    def verify_block(self, index: int) -> bool:
        """Verifies if the block's data matches its checksum."""
        if index < 0 or index >= self.num_blocks:
            raise IndexError("Block index out of bounds.")
        
        block = self.blocks[index]
        if not block["used"]:
            return True # Unused blocks are inherently healthy
            
        expected_checksum = self._compute_checksum(block["data"])
        return expected_checksum == block["checksum"]

    def save_to_json(self, filepath: str = "backup_disk.json") -> None:
        """Saves the current state of the virtual disk to a JSON file."""
        state = {
            "num_blocks": self.num_blocks,
            "block_size": self.block_size,
            "blocks": self.blocks
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=4)

    def load_from_json(self, filepath: str = "backup_disk.json") -> None:
        """Loads the state of the virtual disk from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
                self.num_blocks = state["num_blocks"]
                self.block_size = state["block_size"]
                self.blocks = state["blocks"]
        except FileNotFoundError:
            raise FileNotFoundError(f"Backup file {filepath} not found.")
