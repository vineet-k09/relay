 └──────────────────────────────────┘                            └───────────────────────────────────┘   └───────────────────────────┘
  #### Low-Level Comparison: Local vs. GCS vs. SSH
   Operation            │ Local Filesystem (LocalTransportA… │ Google Cloud Storage (GcsAdapter)   │ GCP Workbench / SSH (SshAdapter)
  ──────────────────────┼────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────
   rename(old, new)     │ os.replace(src, dst) (instant      │ bucket.rename_blob(blob, new_name)  │ ssh.run("mv '{old}' '{new}'")
                        │ inode update)                      │ (server-side rename, 0 network      │ (remote instant move)
                        │                                    │ bytes!)                             │
   copy_local(old, new) │ shutil.copy2(src, dst) (local      │ bucket.copy_blob(blob, bucket,      │ ssh.run("cp '{old}' '{new}'")
                        │ duplicate)                         │ new_name) (server-side duplicate, 0 │ (remote duplicate)
                        │                                    │ network bytes!)                     │
   transfer(path)       │ Read from src_root/path, copy to   │ bucket.blob(path).upload_from_filen │ sftp.put(local_path, remote_path)
                        │ dst_root/path                      │ ame(local_path)                     │
   delete(path)         │ os.remove(path)                    │ bucket.blob(path).delete()          │ ssh.run("rm '{path}'")