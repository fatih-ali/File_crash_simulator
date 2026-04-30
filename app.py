import streamlit as st
import time
import pandas as pd
import os
import json

from disk import VirtualDisk
from filesystem import FileSystem
from crash import CrashSimulator
from recovery import RecoveryEngine
from optimizer import Optimizer

# --- UI Configuration ---
st.set_page_config(layout="wide", page_title="FS Recovery Tool", page_icon="💾")

# --- Custom CSS ---
st.markdown("""
<style>
    .block-grid {
        display: grid;
        grid-template-columns: repeat(8, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .block-cell {
        padding: 15px;
        text-align: center;
        border-radius: 5px;
        font-weight: bold;
        color: white;
    }
    .block-free { background-color: #28a745; }
    .block-used { background-color: #007bff; }
    .block-corrupt { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# --- Initialization ---
def init_system():
    disk = VirtualDisk(32, 64)
    
    # Wipe journal on reset
    if os.path.exists("journal.log"):
        os.remove("journal.log")
        
    fs = FileSystem(disk, "journal.log")
    
    # Load demo data
    demo_files = {
        "readme.txt": "This is a sample readme file for the filesystem demo.",
        "notes.txt": "Study notes: Inodes, Blocks, Journaling, LRU Cache, Defrag.",
        "config.json": '{"version": "1.0", "author": "Student", "theme": "dark"}',
        "data.csv": "name,age,score\\nAlice,20,95\\nBob,22,88\\nCarol,21,92"
    }
    
    for name, content in demo_files.items():
        fs.create_file(name, content)
        
    disk.save_to_json("backup_disk.json")
    
    st.session_state.disk = disk
    st.session_state.fs = fs
    st.session_state.crasher = CrashSimulator(disk, fs)
    st.session_state.recovery = RecoveryEngine(disk, fs)
    st.session_state.optimizer = Optimizer(disk, fs)

if 'disk' not in st.session_state:
    init_system()

disk = st.session_state.disk
fs = st.session_state.fs
crasher = st.session_state.crasher
recovery = st.session_state.recovery
optimizer = st.session_state.optimizer

def render_disk_map(disk_instance):
    html = '<div class="block-grid">'
    for i in range(disk_instance.num_blocks):
        if not disk_instance.verify_block(i):
            css_class = "block-corrupt"
            label = f"{i} (ERR)"
        elif disk_instance.blocks[i]["used"]:
            css_class = "block-used"
            label = f"{i} (USED)"
        else:
            css_class = "block-free"
            label = f"{i} (FREE)"
        html += f'<div class="block-cell {css_class}">{label}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def get_health_percentage():
    healthy = sum(1 for i in range(disk.num_blocks) if disk.verify_block(i))
    return int((healthy / disk.num_blocks) * 100)

# --- Sidebar ---
with st.sidebar:
    st.title("💾 FS Recovery Tool")
    st.caption("Virtual File System & Recovery Simulator")
    
    nav = st.radio("Navigation", 
        ["Dashboard", "File Operations", "Crash Simulator", "Recovery Center", "Optimizer"]
    )
    
    st.divider()
    health = get_health_percentage()
    st.metric("Disk Health", f"{health}%", delta=f"{health-100}%" if health < 100 else "100%")
    st.metric("Files Stored", len(fs.inodes))
    
    if st.button("Reset Disk", type="primary"):
        init_system()
        st.rerun()

# --- Page 1: Dashboard ---
if nav == "Dashboard":
    st.header("System Dashboard")
    
    stats = optimizer.show_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Blocks", stats["total_blocks"])
    col2.metric("Used Blocks", stats["used_blocks"])
    col3.metric("Free Blocks", stats["free_blocks"])
    col4.metric("Files Stored", stats["files"])
    
    # System Status Banner
    health = get_health_percentage()
    if health == 100:
        st.success("System Status: Healthy")
    elif health > 50:
        corrupted = disk.num_blocks - int(health * disk.num_blocks / 100)
        st.warning(f"System Status: Warning - {corrupted} corrupted blocks detected.")
    else:
        st.error("System Status: Critical - Severe corruption detected!")
        
    st.subheader("Disk Block Map")
    render_disk_map(disk)
    
    with st.expander("Recent Journal Activity", expanded=True):
        if os.path.exists("journal.log"):
            with open("journal.log", "r") as f:
                lines = f.readlines()
                recent = lines[-5:] if len(lines) >= 5 else lines
                if recent:
                    for line in reversed(recent):
                        st.code(line.strip(), language="json")
                else:
                    st.info("No journal entries yet.")
        else:
            st.info("No journal log found.")

# --- Page 2: File Operations ---
elif nav == "File Operations":
    st.header("File Operations")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("Create File")
        new_name = st.text_input("Filename", "new_file.txt")
        new_content = st.text_area("Content", "Hello World!")
        if st.button("Create File"):
            try:
                fs.create_file(new_name, new_content)
                st.success(f"File '{new_name}' created successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
                
    with c2:
        st.subheader("Read File")
        files = list(fs.inodes.keys())
        if files:
            read_name = st.selectbox("Select File to Read", files)
            if st.button("Read File"):
                try:
                    content = fs.read_file(read_name)
                    st.code(content)
                    st.json(fs.inodes[read_name])
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No files available.")
            
    with c3:
        st.subheader("Delete File")
        files = list(fs.inodes.keys())
        if files:
            del_name = st.selectbox("Select File to Delete", files)
            if st.button("Delete File"):
                try:
                    fs.delete_file(del_name)
                    st.success(f"File '{del_name}' deleted!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No files available.")
            
    st.divider()
    st.subheader("File Table")
    file_list = fs.list_files()
    if file_list:
        df = pd.DataFrame(file_list)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("The file system is currently empty.")

# --- Page 3: Crash Simulator ---
elif nav == "Crash Simulator":
    st.header("Crash Simulator")
    
    t1, t2, t3 = st.tabs(["Block Corruption", "Metadata Wipe", "Partial Write"])
    
    with t1:
        st.subheader("Simulate Data Corruption")
        corrupt_n = st.slider("Number of blocks to corrupt", 1, 5, 2)
        if st.button("Simulate Block Corruption"):
            with st.spinner("Corrupting blocks..."):
                time.sleep(1)
                corrupted = crasher.crash_type_1_corrupt_blocks(corrupt_n)
            if corrupted:
                st.error(f"Corrupted blocks: {corrupted}")
            else:
                st.warning("No used blocks available to corrupt.")
            render_disk_map(disk)
            
    with t2:
        st.subheader("Simulate Metadata Wipe")
        st.warning("This will clear the entire Inode table! The filesystem will lose track of all files.")
        confirm = st.checkbox("I understand the consequences")
        if st.button("Wipe Metadata", disabled=not confirm):
            count_before = len(fs.inodes)
            with st.spinner("Wiping metadata..."):
                time.sleep(1)
                crasher.crash_type_2_wipe_metadata()
            st.error(f"Metadata wiped. Files before: {count_before}, Files after: 0")
            
    with t3:
        st.subheader("Simulate Partial Write")
        p_name = st.text_input("Filename (Partial)", "broken_file.txt")
        p_content = st.text_area("Content (will be cut in half)", "This is a very long string that will only be partially written to the disk.")
        if st.button("Simulate Partial Write"):
            with st.spinner("Writing..."):
                time.sleep(0.5)
                try:
                    crasher.crash_type_3_partial_write(p_name, p_content)
                    st.error("Power failure! Write interrupted.")
                    render_disk_map(disk)
                except Exception as e:
                    st.error(f"Error: {e}")

# --- Page 4: Recovery Center ---
elif nav == "Recovery Center":
    st.header("Recovery Center")
    
    t1, t2, t3, t4, t5 = st.tabs(["Scan & Detect", "Restore Backup", "Journal Replay", "Repair Blocks", "Reconstruct Metadata"])
    
    with t1:
        st.subheader("Scan Disk Integrity")
        if st.button("Scan Disk"):
            with st.spinner("Scanning..."):
                time.sleep(1)
                bad_blocks = recovery.scan_disk()
            if bad_blocks:
                st.error(f"Scan complete. Corrupted blocks found: {bad_blocks}")
                # Show table
                status_data = [{"Block": i, "Status": "CORRUPTED" if i in bad_blocks else "OK"} for i in range(disk.num_blocks)]
                df = pd.DataFrame(status_data)
                
                # Apply style for dataframe correctly in newer pandas/streamlit
                def color_corrupted(val):
                    color = '#ffcccc' if val == 'CORRUPTED' else ''
                    return f'background-color: {color}'
                    
                st.dataframe(df.style.map(color_corrupted, subset=["Status"]))
            else:
                st.success("Scan complete. All blocks are healthy.")
                
    with t2:
        st.subheader("Restore from Backup")
        if st.button("Restore Backup"):
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i + 1)
            try:
                recovery.recover_from_backup()
                st.success("Disk restored from backup successfully!")
                render_disk_map(disk)
            except Exception as e:
                st.error(f"Error: {e}")
                
    with t3:
        st.subheader("Journal Replay")
        if os.path.exists(fs.journal_path):
            entries = []
            with open(fs.journal_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            if entries:
                st.dataframe(pd.DataFrame(entries))
            
            if st.button("Replay Journal"):
                with st.spinner("Replaying..."):
                    time.sleep(1.5)
                    recovery.recover_from_journal()
                st.success("Journal replay complete! System state reconstructed.")
                st.rerun()
        else:
            st.info("No journal found.")
            
    with t4:
        st.subheader("Repair Corrupted Blocks")
        bad_blocks = recovery.scan_disk()
        if bad_blocks:
            st.warning(f"Corrupted blocks detected: {bad_blocks}")
            if st.button("Repair All"):
                with st.spinner("Repairing..."):
                    time.sleep(1)
                    damaged = recovery.repair_corrupted_blocks(bad_blocks)
                st.success(f"Repaired blocks. Affected files marked as damaged: {damaged}")
                st.rerun()
        else:
            st.success("No corrupted blocks to repair.")
            
    with t5:
        st.subheader("Reconstruct Metadata")
        st.info("If the inode table was lost but the journal is intact, you can reconstruct the metadata.")
        if st.button("Reconstruct Now"):
            with st.spinner("Reconstructing..."):
                time.sleep(1)
                recovered = recovery.reconstruct_metadata()
            st.success(f"Metadata reconstructed! Recovered files: {recovered}")

# --- Page 5: Optimizer ---
elif nav == "Optimizer":
    st.header("System Optimizer")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("LRU Cache")
        files = list(fs.inodes.keys())
        if files:
            opt_file = st.selectbox("Select File", files, key="opt_sel")
            if st.button("Read (Cached)"):
                content, is_hit = optimizer.cached_read(opt_file)
                if is_hit:
                    st.success("Cache HIT! 🚀")
                else:
                    st.warning("Cache MISS! 🐌 (Read from disk and cached)")
                st.code(content)
        
        st.markdown("**Current Cache Contents:**")
        cache_items = list(optimizer.cache.cache.keys())
        if cache_items:
            for i, item in enumerate(reversed(cache_items)):
                st.markdown(f"{i+1}. `{item}`")
        else:
            st.info("Cache is empty.")
            
    with col2:
        st.subheader("Defragmentation")
        score_before = optimizer.disk_fragmentation_score()
        st.metric("Fragmentation Score", score_before)
        
        if st.button("Defragment"):
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i + 1)
            optimizer.defragment()
            score_after = optimizer.disk_fragmentation_score()
            st.success(f"Defragmentation complete! Score: {score_before} -> {score_after}")
            st.rerun()
            
        st.subheader("Disk Layout")
        render_disk_map(disk)
        
    st.divider()
    st.subheader("Stats Dashboard")
    stats = optimizer.show_stats()
    
    chart_data = pd.DataFrame({
        "Blocks": ["Used", "Free"],
        "Count": [stats["used_blocks"], stats["free_blocks"]]
    })
    st.bar_chart(chart_data.set_index("Blocks"))
