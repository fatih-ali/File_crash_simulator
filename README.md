# File System Recovery and Optimization Tool

A web-based interactive tool built with Python and Streamlit that simulates a virtual disk, demonstrates disk crash scenarios, applies recovery mechanisms, and optimizes file read/write performance using efficient data structures.

## Setup Instructions

1. Ensure you have Python 3.10+ installed.
2. Install the required dependency (Streamlit):
   ```bash
   pip install streamlit
   ```

## How to Run

Navigate to the project directory and run:
```bash
streamlit run app.py
```
The application will open in your default web browser.

## Features

- **Virtual Disk**: Simulates a disk with 32 blocks (64 bytes each). Tracks allocation, used space, and checksums to ensure data integrity.
- **File System**: Maps files to blocks using an Inode table and maintains a Write-Ahead Journal (`journal.log`) to log operations before execution.
- **Crash Simulator**: Allows you to simulate data corruption, metadata wipes, and partial writes to observe how a filesystem handles failures.
- **Recovery Engine**: Scans the disk for corruption, repairs damaged blocks, restores backups, and reconstructs metadata from the journal.
- **Optimizer**: Features an LRU Cache to speed up frequently read files and a defragmentation tool to reorganize non-contiguous file blocks into sequential space.

## Concepts Explained

- **Blocks**: The smallest addressable unit on the disk.
- **Inodes**: Data structures storing metadata about files, including which blocks contain the file's data.
- **Write-Ahead Journaling**: A technique where changes are written to a log before they are applied to the filesystem, enabling recovery in case of a crash.
- **Checksums (MD5)**: A hash function used to verify that a block's data hasn't been altered or corrupted.
- **LRU Cache**: "Least Recently Used" Cache. It keeps the most recently accessed files in memory, evicting the oldest when the cache is full to prevent unnecessary disk reads.
- **Defragmentation**: Reordering file blocks so they sit contiguously on the disk, theoretically improving read/write speed on mechanical drives and organizing free space.

# File_crash_simulator
"# File_crash_simulator" 
"# File_crash_simulator" 
