Terminal 1
```ps1
PS C:\Users\KushwahaV2> iaptunnel
WARNING:

To increase the performance of the tunnel, consider installing NumPy. For instructions,
please see https://cloud.google.com/iap/docs/using-tcp-forwarding#increasing_the_tcp_upload_bandwidth

Testing if tunnel connection works.
Listening on port [2222].
```

Terminal 2
```ps1
PS C:\Users\KushwahaV2\Downloads\relay> gcloud compute os-login describe-profile
name: '114863201964357192953'
posixAccounts:
- gid: '1205294880'
  homeDirectory: /home/vineet_kushwaha1_<redacted>_com
  operatingSystemType: LINUX
  primary: true
  uid: '1205294880'
  username: vineet_kushwaha1_<redacted>_com
sshPublicKeys:
  <reacted>:
    fingerprint: <reacted>
    key: |
      ssh-rsa <redacted> VF-ROOT\KushwahaV2@E1416948
    name: users/114863201964357192953/sshPublicKeys/<reacted>:
    fingerprint: <reacted>
    key: ssh-rsa <reacted>
      vineet_kushwaha1@cs-492332795803-default
    name: users/114863201964357192953/sshPublicKeys/<reacted>:
    fingerprint: <reacted>
    key: ssh-rsa <reacted>
      VF-ROOT\KushwahaV2@E1416948
    name: users/114863201964357192953/sshPublicKeys/<reacted>
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay> ssh -p 2222 -i "$HOME\.ssh\google_compute_engine" -o BatchMode=yes vineet_kushwaha1_<redacted>.com@127.0.0.1 "pwd && python3 --version"
Host key verification failed.
PS C:\Users\KushwahaV2\Downloads\relay> ssh-keygen -F "[127.0.0.1]:2222"
PS C:\Users\KushwahaV2\Downloads\relay> ssh-keygen -R "[127.0.0.1]:2222"
Host [127.0.0.1]:2222 not found in C:\\Users\\KushwahaV2/.ssh/known_hosts
PS C:\Users\KushwahaV2\Downloads\relay> ssh -p 2222 `
>>     -i "$HOME\.ssh\google_compute_engine" `
>>     vineet_kushwaha1_<redacted>_com@127.0.0.1
The authenticity of host '[127.0.0.1]:2222 ([127.0.0.1]:2222)' can't be established.
ED25519 key fingerprint is SHA256:<reacted>.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added '[127.0.0.1]:2222' (ED25519) to the list of known hosts.

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Creating directory '/home/vineet_kushwaha1_<redacted>_com'.
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls -a
.  ..  .bash_logout  .bashrc  .config  .docker  .profile
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ cd ..
vineet_kushwaha1_<redacted>_com@vineet-k-instance:/home$ ls
jupyter  <reacted>  vineet_kushwaha1_<redacted>_com
vineet_kushwaha1_<redacted>_com@vineet-k-instance:/home$ cd ~
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls ../home/jupyter/
ls: cannot access '../home/jupyter/': No such file or directory
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls ../home
ls: cannot access '../home': No such file or directory
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls ../
jupyter  <reacted>  vineet_kushwaha1_<redacted>_com
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ ls ../jupyter
be.zip                   hld_frontend_section.md  vf-commentary-assistance-be
find_char_at_88630.py    package.json             vf-commentary-assistance-be.zip
find_unescaped_u_new.py  relay                    vf-mc2-aa-de-sales-agent-frontend
fix_syntax.py            verify-versions.sh       webpack.config.js
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ exit
logout
Connection to 127.0.0.1 closed.
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay> ssh -p 2222 -i "$HOME\.ssh\google_compute_engine" -o BatchMode=yes vineet_kushwaha1_<redacted>_com@127.0.0.1 "pwd && python3 --version"
/home/vineet_kushwaha1_<redacted>_com
Python 3.11.2
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay> ls

    Directory: C:\Users\KushwahaV2\Downloads\relay


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/14/2026  12:29 AM                relay
d-----        11/13/2026  11:48 PM                win_amd64_whl
-a----         11/9/2026  10:38 AM          20480 .relay.db

PS C:\Users\KushwahaV2\Downloads\relay> relay sync . "ssh vineet_kushwaha1_<redacted>_com@localhost:2222/../jupyter/relay/" --dry-run
[relay] Resolving endpoints:
    Source:      . [LOCAL]
    Destination: ssh vineet_kushwaha1_<redacted>_com@localhost:2222/../jupyter/relay/ [SSH]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | relay/.python-version          |
ADDED        | relay/CONTEXT.md               |
...

Planned changes:
  • 82 to add

[dry-run] Dry run active. No changes applied.
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay> relay sync . "ssh vineet_kushwaha1_<redacted>_com@localhost:2222/../jupyter/relay/"
[relay] Resolving endpoints:
    Source:      . [LOCAL]
    Destination: ssh vineet_kushwaha1_<redacted>_com@localhost:2222/../jupyter/relay/ [SSH]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | relay/.python-version          |
ADDED        | relay/CONTEXT.md               |
...

Planned changes:
  • 82 to add
[error] Command '['ssh', '-p', '2222', '-i', 'C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'BatchMode=yes', 'vineet_kushwaha1_<redacted>_com@localhost', 'mkdir -p ../jupyter/relay/relay']' returned non-zero exit status 255.
```

Terminal 2 
```ps1
PS C:\Users\KushwahaV2> iaptunnel
WARNING:

To increase the performance of the tunnel, consider installing NumPy. For instructions,
please see https://cloud.google.com/iap/docs/using-tcp-forwarding#increasing_the_tcp_upload_bandwidth

Testing if tunnel connection works.
Listening on port [2222].
ERROR: [0] Error during local connection to [('127.0.0.1', 56406)]: [WinError 10054] An existing connection was forcibly closed by the remote host
Traceback (most recent call last):
  File "C:\Program Files\Google\google-cloud-sdk\lib\googlecloudsdk\command_lib\compute\iap_tunnel.py", line 793, in RunReceiveLocalData
    data = conn.recv(utils.SUBPROTOCOL_MAX_DATA_FRAME_SIZE)
ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host
ERROR: [1] Error during local connection to [('127.0.0.1', 53596)]: [WinError 10054] An existing connection was forcibly closed by the remote host
Traceback (most recent call last):
  File "C:\Program Files\Google\google-cloud-sdk\lib\googlecloudsdk\command_lib\compute\iap_tunnel.py", line 793, in RunReceiveLocalData
    data = conn.recv(utils.SUBPROTOCOL_MAX_DATA_FRAME_SIZE)
ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host
```

Terminal 3
```ps1
PS C:\Users\KushwahaV2> ssh-keygen -R "[localhost]:2222"
# Host [localhost]:2222 found: line 1
# Host [localhost]:2222 found: line 2
C:\Users\KushwahaV2/.ssh/known_hosts updated.
Original contents retained as C:\Users\KushwahaV2/.ssh/known_hosts.old
PS C:\Users\KushwahaV2> ssh -p 2222 `
>>   -i "$HOME\.ssh\google_compute_engine" `
>>   -o StrictHostKeyChecking=accept-new `
>>   vineet_kushwaha1_<redacted>_com@localhost
Warning: Permanently added '[localhost]:2222' (ED25519) to the list of known hosts.

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Wed Nov 25 08:37:12 2026 from 35.235.240.97
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ exit
logout
Connection to localhost closed.
PS C:\Users\KushwahaV2> ssh `
>>   -p 2222 `
>>   -i "$HOME\.ssh\google_compute_engine" `
>>   -o StrictHostKeyChecking=accept-new `
>>   -o BatchMode=yes `
>>   vineet_kushwaha1_<redacted>_com@localhost `
>>   "mkdir -p /relay/relay && echo success"
mkdir: cannot create directory ‘/relay’: Permission denied
PS C:\Users\KushwahaV2>
```
Terminal 4
```ps1
PS C:\Users\KushwahaV2\Downloads\relay> ssh -vvv `
>>   -p 2222 `
>>   -i "$HOME\.ssh\google_compute_engine" `
>>   -o StrictHostKeyChecking=accept-new `
>>   vineet_kushwaha1_<redacted>_com@localhost
OpenSSH_for_Windows_9.5p2, LibreSSL 3.8.2
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/config error:2
debug3: Failed to open file:C:/ProgramData/ssh/ssh_config error:2
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts' -> 'C:\\Users\\KushwahaV2/.ssh/known_hosts'
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts2' -> 'C:\\Users\\KushwahaV2/.ssh/known_hosts2'
debug2: resolving "localhost" port 2222
debug3: resolve_host: lookup localhost:2222
debug3: ssh_connect_direct: entering
debug1: Connecting to localhost [::1] port 2222.
debug1: Connection established.
debug1: identity file C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine type 0
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/google_compute_engine-cert error:2
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/google_compute_engine-cert.pub error:2
debug3: failed to open file:C:/Users/KushwahaV2/.ssh/google_compute_engine-cert error:2
debug1: identity file C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine-cert type -1
debug1: Local version string SSH-2.0-OpenSSH_for_Windows_9.5
debug1: Remote protocol version 2.0, remote software version OpenSSH_9.2p1 Debian-2+deb12u10
debug1: compat_banner: match: OpenSSH_9.2p1 Debian-2+deb12u10 pat OpenSSH* compat 0x04000000
debug2: fd 3 setting O_NONBLOCK
debug1: Authenticating to localhost:2222 as 'vineet_kushwaha1_<redacted>_com'
debug3: put_host_port: [localhost]:2222
debug3: record_hostkey: found key type ED25519 in file C:\\Users\\KushwahaV2/.ssh/known_hosts:4
debug3: load_hostkeys_file: loaded 1 keys from [localhost]:2222
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/known_hosts2 error:2
debug1: load_hostkeys: fopen C:\\Users\\KushwahaV2/.ssh/known_hosts2: No such file or directory
debug3: Failed to open file:C:/ProgramData/ssh/ssh_known_hosts error:2
debug1: load_hostkeys: fopen __PROGRAMDATA__\\ssh/ssh_known_hosts: No such file or directory
debug3: Failed to open file:C:/ProgramData/ssh/ssh_known_hosts2 error:2
debug1: load_hostkeys: fopen __PROGRAMDATA__\\ssh/ssh_known_hosts2: No such file or directory
debug3: order_hostkeyalgs: have matching best-preference key type ssh-ed25519-cert-v01@openssh.com, using HostkeyAlgorithms verbatim
debug3: send packet: type 20
debug1: SSH2_MSG_KEXINIT sent
debug3: receive packet: type 20
debug1: SSH2_MSG_KEXINIT received
debug2: local client KEXINIT proposal
debug2: KEX algorithms: curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,ext-info-c,kex-strict-c-v00@openssh.com
debug2: host key algorithms: ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512
debug2: compression ctos: none,zlib@openssh.com,zlib
debug2: compression stoc: none,zlib@openssh.com,zlib
debug2: languages ctos:
debug2: languages stoc:
debug2: first_kex_follows 0
debug2: reserved 0
debug2: peer server KEXINIT proposal
debug2: KEX algorithms: sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,kex-strict-s-v00@openssh.com
debug2: host key algorithms: rsa-sha2-512,rsa-sha2-256,ecdsa-sha2-nistp256,ssh-ed25519
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos:
debug2: languages stoc:
debug2: first_kex_follows 0
debug2: reserved 0
debug3: kex_choose_conf: will use strict KEX ordering
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: ssh-ed25519
debug1: kex: server->client cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug1: kex: client->server cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug3: send packet: type 30
debug1: expecting SSH2_MSG_KEX_ECDH_REPLY
debug3: receive packet: type 31
debug1: SSH2_MSG_KEX_ECDH_REPLY received
debug1: Server host key: ssh-ed25519 SHA256:<redacted>+g
debug3: put_host_port: [::1]:2222
debug3: put_host_port: [localhost]:2222
debug3: record_hostkey: found key type ED25519 in file C:\\Users\\KushwahaV2/.ssh/known_hosts:4
debug3: load_hostkeys_file: loaded 1 keys from [localhost]:2222
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/known_hosts2 error:2
debug1: load_hostkeys: fopen C:\\Users\\KushwahaV2/.ssh/known_hosts2: No such file or directory
debug3: Failed to open file:C:/ProgramData/ssh/ssh_known_hosts error:2
debug1: load_hostkeys: fopen __PROGRAMDATA__\\ssh/ssh_known_hosts: No such file or directory
debug3: Failed to open file:C:/ProgramData/ssh/ssh_known_hosts2 error:2
debug1: load_hostkeys: fopen __PROGRAMDATA__\\ssh/ssh_known_hosts2: No such file or directory
debug1: Host '[localhost]:2222' is known and matches the ED25519 host key.
debug1: Found key in C:\\Users\\KushwahaV2/.ssh/known_hosts:4
debug3: send packet: type 21
debug1: ssh_packet_send2_wrapped: resetting send seqnr 3
debug2: ssh_set_newkeys: mode 1
debug1: rekey out after 134217728 blocks
debug1: SSH2_MSG_NEWKEYS sent
debug1: expecting SSH2_MSG_NEWKEYS
debug3: receive packet: type 21
debug1: ssh_packet_read_poll2: resetting read seqnr 3
debug1: SSH2_MSG_NEWKEYS received
debug2: ssh_set_newkeys: mode 0
debug1: rekey in after 134217728 blocks
debug3: ssh_get_authentication_socket_path: path '\\\\.\\pipe\\openssh-ssh-agent'
debug3: unable to connect to pipe \\\\.\\pipe\\openssh-ssh-agent, error: 2
debug1: get_agent_identities: ssh_get_authentication_socket: No such file or directory
debug1: Will attempt key: C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine RSA SHA256:<redacted>/o6F0soSHoDUKRwpE/XDtVV4/ssdHMZY explicit
debug2: pubkey_prepare: done
debug3: send packet: type 5
debug3: receive packet: type 7
debug1: SSH2_MSG_EXT_INFO received
debug1: kex_input_ext_info: server-sig-algs=<ssh-ed25519,sk-ssh-ed25519@openssh.com,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ecdsa-sha2-nistp256@openssh.com,webauthn-sk-ecdsa-sha2-nistp256@openssh.com,ssh-dss,ssh-rsa,rsa-sha2-256,rsa-sha2-512>
debug1: kex_ext_info_check_ver: publickey-hostbound@openssh.com=<0>
debug3: receive packet: type 6
debug2: service_accept: ssh-userauth
debug1: SSH2_MSG_SERVICE_ACCEPT received
debug3: send packet: type 50
debug3: receive packet: type 51
debug1: Authentications that can continue: publickey
debug3: start over, passed a different list publickey
debug3: preferred publickey,keyboard-interactive,password
debug3: authmethod_lookup publickey
debug3: remaining preferred: keyboard-interactive,password
debug3: authmethod_is_enabled publickey
debug1: Next authentication method: publickey
debug1: Offering public key: C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine RSA SHA256:<redacted>/o6F0soSHoDUKRwpE/XDtVV4/ssdHMZY explicit
debug3: send packet: type 50
debug2: we sent a publickey packet, wait for reply
debug3: receive packet: type 60
debug1: Server accepts key: C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine RSA SHA256:<redacted>/o6F0soSHoDUKRwpE/XDtVV4/ssdHMZY explicit
debug3: sign_and_send_pubkey: using publickey-hostbound-v00@openssh.com with RSA SHA256:<redacted>/o6F0soSHoDUKRwpE/XDtVV4/ssdHMZY
debug3: sign_and_send_pubkey: signing using rsa-sha2-512 SHA256:<redacted>/o6F0soSHoDUKRwpE/XDtVV4/ssdHMZY
debug3: send packet: type 50
debug3: receive packet: type 52
Authenticated to localhost ([::1]:2222) using "publickey".
debug1: channel 0: new session [client-session] (inactive timeout: 0)
debug3: ssh_session2_open: channel_new: 0
debug2: channel 0: send open
debug3: send packet: type 90
debug1: Requesting no-more-sessions@openssh.com
debug3: send packet: type 80
debug1: Entering interactive session.
debug1: pledge: filesystem
debug3: client_repledge: enter
debug1: ENABLE_VIRTUAL_TERMINAL_INPUT is supported. Reading the VTSequence from console
debug3: This windows OS supports conpty
debug1: ENABLE_VIRTUAL_TERMINAL_PROCESSING is supported. Console supports the ansi parsing
debug3: Successfully set console output code page from:65001 to 65001
debug3: Successfully set console input code page from:437 to 65001
debug3: receive packet: type 80
debug1: client_input_global_request: rtype hostkeys-00@openssh.com want_reply 0
debug3: client_input_hostkeys: received RSA key SHA256:<redacted>+Kkcyl18
debug3: client_input_hostkeys: received ECDSA key SHA256:<redacted>/U78ZkpJg6twy80XsctPXds
debug3: client_input_hostkeys: received ED25519 key SHA256:<redacted>+g
debug3: put_host_port: [localhost]:2222
debug1: client_input_hostkeys: searching C:\\Users\\KushwahaV2/.ssh/known_hosts for [localhost]:2222 / (none)
debug3: hostkeys_foreach: reading file "C:\\Users\\KushwahaV2/.ssh/known_hosts"
debug3: hostkeys_find: found ssh-ed25519 key under different name/addr at C:\\Users\\KushwahaV2/.ssh/known_hosts:1
debug3: hostkeys_find: found ssh-rsa key under different name/addr at C:\\Users\\KushwahaV2/.ssh/known_hosts:2
debug3: hostkeys_find: found ecdsa-sha2-nistp256 key under different name/addr at C:\\Users\\KushwahaV2/.ssh/known_hosts:3
debug3: hostkeys_find: found ssh-ed25519 key at C:\\Users\\KushwahaV2/.ssh/known_hosts:4
debug1: client_input_hostkeys: searching C:\\Users\\KushwahaV2/.ssh/known_hosts2 for [localhost]:2222 / (none)
debug3: Failed to open file:C:/Users/KushwahaV2/.ssh/known_hosts2 error:2
debug1: client_input_hostkeys: hostkeys file C:\\Users\\KushwahaV2/.ssh/known_hosts2 does not exist
debug3: client_input_hostkeys: 3 server keys: 2 new, 18446744073709551615 retained, 2 incomplete match. 0 to remove
debug1: client_input_hostkeys: host key found matching a different name/address, skipping UserKnownHostsFile update
debug3: client_repledge: enter
debug3: receive packet: type 4
debug1: Remote: /usr/bin/google_authorized_keys:1: key options: agent-forwarding port-forwarding pty user-rc x11-forwarding
debug3: receive packet: type 4
debug1: Remote: /usr/bin/google_authorized_keys:1: key options: agent-forwarding port-forwarding pty user-rc x11-forwarding
debug3: receive packet: type 91
debug2: channel_input_open_confirmation: channel 0: callback start
debug2: fd 3 setting TCP_NODELAY
debug2: client_session2_setup: id 0
debug2: channel 0: request pty-req confirm 1
debug3: send packet: type 98
debug2: channel 0: request shell confirm 1
debug3: send packet: type 98
debug3: client_repledge: enter
debug1: pledge: fork
debug2: channel_input_open_confirmation: channel 0: callback done
debug2: channel 0: open confirm rwindow 0 rmax 32768
debug3: receive packet: type 99
debug2: channel_input_status_confirm: type 99 id 0
debug2: PTY allocation request accepted on channel 0
debug2: channel 0: rcvd adjust 2097152
debug3: receive packet: type 99
debug2: channel_input_status_confirm: type 99 id 0
debug2: shell request accepted on channel 0

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Wed Nov 25 08:53:35 2026 from 35.235.248.224
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$ debug3: receive packet: type 98
debug1: client_input_channel_req: channel 0 rtype keepalive@openssh.com reply 1
debug3: send packet: type 100
debug3: receive packet: type 98
debug1: client_input_channel_req: channel 0 rtype keepalive@openssh.com reply 1
debug3: send packet: type 100
debug2: client_check_window_change: changed
debug2: channel 0: request window-change confirm 0
debug3: send packet: type 98
vineet_kushwaha1_<redacted>_com@vineet-k-instance:~$
```
Terminal 2

```ps1
PS C:\Users\KushwahaV2\Downloads\relay> relay sync . "ssh vineet_kushwaha1_<redacted>_com@localhost:2222/relay"
[relay] Resolving endpoints:
    Source:      . [LOCAL]
    Destination: ssh vineet_kushwaha1_<redacted>_com@localhost:2222/relay [SSH]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | relay/.python-version          |
ADDED        | relay/CONTEXT.md               |
...

Planned changes:
  • 82 to add
[error] Command '['ssh', '-p', '2222', '-i', 'C:\\Users\\KushwahaV2\\.ssh\\google_compute_engine', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'BatchMode=yes', 'vineet_kushwaha1_<redacted>_com@localhost', 'mkdir -p relay/relay']' returned non-zero exit status 255.
```