from collections import OrderedDict
from disk import VirtualDisk
from filesystem import FileSystem

class LRUCache:
    """
    Least Recently Used (LRU) Cache using OrderedDict.
    Caches the content of frequently read files to avoid disk reads.
    """
    def __init__(self, capacity: int = 4):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.eviction_log = []

    def get(self, key: str) -> str | None:
        """Returns the value if key exists, updating its access order."""
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: str) -> None:
        """Adds a key-value pair, evicting the oldest if capacity is reached."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            oldest = next(iter(self.cache))
            self.eviction_log.append(f"Evicted: {oldest}")
            del self.cache[oldest]

    def clear(self) -> None:
        self.cache.clear()
        self.eviction_log.clear()

class Optimizer:
    """
    Optimizes disk performance via caching and defragmentation.
    """
    def __init__(self, disk: VirtualDisk, fs: FileSystem):
        self.disk = disk
        self.fs = fs
        self.cache = LRUCache(capacity=4)
        self.hits = 0
        self.misses = 0

    def cached_read(self, filename: str) -> tuple[str, bool]:
        """
        Attempts to read from cache. If miss, reads from FS and stores in cache.
        Returns (content, is_hit).
        """
        cached_content = self.cache.get(filename)
        if cached_content is not None:
            self.hits += 1
            return cached_content, True
            
        # Cache Miss
        self.misses += 1
        content = self.fs.read_file(filename)
        self.cache.put(filename, content)
        return content, False

    def disk_fragmentation_score(self) -> int:
        """
        Calculates the number of files whose blocks are not perfectly contiguous.
        """
        score = 0
        for name, inode in self.fs.inodes.items():
            blocks = inode["blocks"]
            if not blocks:
                continue
            is_contiguous = True
            for i in range(1, len(blocks)):
                if blocks[i] != blocks[i-1] + 1:
                    is_contiguous = False
                    break
            if not is_contiguous:
                score += 1
        return score

    def defragment(self) -> None:
        """
        Moves all file blocks to be contiguous starting from block 0.
        """
        # Step 1: Read all files into memory
        files_data = {}
        for name in self.fs.inodes:
            files_data[name] = self.fs.read_file(name)
            
        # Step 2: Clear disk and inodes in memory (we will rewrite them)
        # We don't wipe the journal because defrag is a maintenance op
        for i in range(self.disk.num_blocks):
            self.disk.free_block(i)
            
        old_inodes = self.fs.inodes.copy()
        self.fs.inodes.clear()
        
        # Step 3: Write files back sequentially
        for name, content in files_data.items():
            # Calculate needed blocks
            size = len(content)
            if size == 0:
                blocks_needed = 0
            else:
                blocks_needed = (size + self.disk.block_size - 1) // self.disk.block_size
            
            allocated = []
            if blocks_needed > 0:
                allocated = self.disk.allocate_blocks(blocks_needed)
            
            # Write data
            for i, block_idx in enumerate(allocated):
                start = i * self.disk.block_size
                end = start + self.disk.block_size
                chunk = content[start:end]
                self.disk.write_block(block_idx, chunk)
                
            # Restore inode with new blocks
            old_inode = old_inodes[name]
            old_inode["blocks"] = allocated
            self.fs.inodes[name] = old_inode

    def show_stats(self) -> dict:
        """Returns statistics about the disk and cache."""
        used = sum(1 for block in self.disk.blocks if block["used"])
        free = self.disk.num_blocks - used
        return {
            "total_blocks": self.disk.num_blocks,
            "used_blocks": used,
            "free_blocks": free,
            "files": len(self.fs.inodes),
            "fragments": self.disk_fragmentation_score(),
            "cache_size": len(self.cache.cache)
        }
