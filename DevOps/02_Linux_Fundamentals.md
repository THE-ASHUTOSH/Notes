# Session 2 — Linux Fundamentals 🐧

> **Linux is the heart of DevOps.** Almost every server, container base image, CI runner and
> Kubernetes node is Linux. If you are shaky here, everything above it (Docker, K8s, Terraform)
> becomes guesswork.

---

## 📑 Table of Contents
1. [Why Linux for DevOps](#-why-linux-for-devops)
2. [Linux Architecture](#-linux-architecture)
3. [The Linux File System](#-the-linux-file-system-fhs)
4. [Essential Commands — File & Directory](#1-file--directory-commands)
5. [File Viewing & Search](#2-file-viewing--search)
6. [Users, Groups & Permissions](#-users-groups--permissions)
7. [Processes](#-processes)
8. [Services (systemd)](#-services-systemd)
9. [Package Management](#-package-management)
10. [Disk & Storage](#-disk--storage)
11. [Networking Commands](#-networking-commands)
12. [Logs & Basic Troubleshooting](#-logs--basic-troubleshooting)
13. [Scheduling & Background Jobs](#-scheduling--background-jobs)
14. [System Information](#-system-information--utilities)
15. [Advanced / Performance Commands](#-advanced-monitoring--performance)
16. [SSH & File Transfer](#-ssh--secure-file-transfer)
17. [Shortcuts & Pro Tips](#-shortcuts--pro-tips)
18. [Troubleshooting Playbook](#-troubleshooting-playbook)

---

## 🎯 Why Linux for DevOps

| Reason | Detail |
|---|---|
| **It runs the internet** | The overwhelming majority of servers, cloud VMs and containers are Linux. |
| **Containers *are* Linux** | Docker uses Linux kernel features — **namespaces** (isolation) and **cgroups** (resource limits). Container images are Linux userlands. |
| **Everything is a file** | Devices, sockets, processes and kernel state are exposed as files (`/proc`, `/sys`, `/dev`) — so the same tools work on everything. |
| **Scriptable & composable** | Small tools + pipes = automation. This is the basis of shell scripting (Session 3). |
| **Free & open source** | No licensing barrier to running 1000 nodes. |
| **Stable & secure** | Long-term support releases, fine-grained permission model. |

**Common distributions you'll meet**

| Family | Distros | Package manager | Typical use |
|---|---|---|---|
| **Debian** | Debian, **Ubuntu** | `apt` / `dpkg` (`.deb`) | Most popular for cloud VMs & CI |
| **Red Hat** | RHEL, **CentOS**, Rocky, Fedora, Amazon Linux | `yum` / `dnf` / `rpm` (`.rpm`) | Enterprise servers |
| **Alpine** | Alpine Linux | `apk` | **Container base images** (~5 MB!) |
| **SUSE** | SLES, openSUSE | `zypper` | Enterprise (Europe-heavy) |

---

## 🏗️ Linux Architecture

```
┌────────────────────────────────────────────┐
│  User Applications (nginx, python, git)    │
├────────────────────────────────────────────┤
│  Shell (bash / zsh / sh)  +  Utilities     │   ← where you work
├────────────────────────────────────────────┤
│  System Libraries (glibc / musl)           │
├────────────────────────────────────────────┤
│  KERNEL                                    │   ← process/memory/device/
│  process mgmt · memory mgmt · filesystem   │     network management
│  device drivers · networking stack         │
├────────────────────────────────────────────┤
│  Hardware (CPU, RAM, Disk, NIC)            │
└────────────────────────────────────────────┘
```

- **Kernel** — the core: schedules processes, manages memory, talks to hardware.
- **Shell** — the command interpreter that turns your typing into system calls. `bash` is the default.
- **Utilities** — the small programs (`ls`, `grep`, `awk`) that do one job well.

> 💡 A **container** shares the host **kernel** but has its own userland (shell + libraries +
> utilities). That is precisely why containers are megabytes and VMs are gigabytes.

---

## 📂 The Linux File System (FHS)

Linux uses a **single inverted tree** starting at root `/` — there are no drive letters like `C:\`.

```
/
├── bin      → essential user binaries (ls, cp, cat)          [often → /usr/bin]
├── sbin     → essential SYSTEM binaries (ip, mount, reboot)   [root-only tools]
├── boot     → kernel + bootloader (vmlinuz, grub)
├── dev      → device files (/dev/sda, /dev/null, /dev/random)
├── etc      → ⭐ ALL system CONFIGURATION files (text!)
│   ├── passwd, shadow, group        → users & groups
│   ├── hosts, resolv.conf           → static DNS / nameservers
│   ├── fstab                        → filesystems to mount at boot
│   ├── ssh/sshd_config              → SSH server config
│   ├── nginx/, systemd/, cron.d/    → per-service config
│   └── os-release                   → which distro & version
├── home     → normal users' home dirs (/home/ashutosh)
├── root     → the root user's home dir (NOT /)
├── lib      → shared libraries (.so) needed by /bin and /sbin
├── media    → auto-mounted removable media (USB, CD)
├── mnt      → manual temporary mount point
├── opt      → optional / third-party software (self-contained)
├── proc     → ⭐ VIRTUAL fs: live kernel & process info (/proc/cpuinfo, /proc/<pid>/)
├── sys      → VIRTUAL fs: kernel/device tree (used by cgroups → containers)
├── srv      → data served by services (e.g. web/ftp payloads)
├── tmp      → temporary files, world-writable, wiped on reboot
├── usr      → user programs & read-only data
│   ├── bin, sbin, lib               → the bulk of installed software
│   ├── local/                       → software YOU compiled/installed manually
│   └── share/                       → docs, icons, static data (nginx html lives here)
└── var      → ⭐ VARIABLE data that changes at runtime
    ├── log/                         → LOG FILES (syslog, messages, nginx/, auth.log)
    ├── lib/                         → app state — incl. /var/lib/docker (!)
    ├── cache/, spool/, tmp/         → caches, print/mail queues
    └── run/                         → PID files, sockets
```

### The 5 directories a DevOps engineer lives in
| Path | Why |
|---|---|
| **`/etc`** | Every config change starts here |
| **`/var/log`** | Every troubleshooting session starts here |
| **`/home`** | Your workspace, SSH keys (`~/.ssh`) |
| **`/proc` & `/sys`** | Live system truth; cgroups/namespaces = container internals |
| **`/var/lib/docker`** | Where Docker stores images, containers and **volumes** |

### Path concepts
| Concept | Meaning | Example |
|---|---|---|
| **Absolute path** | Starts at `/`, unambiguous | `/var/log/syslog` |
| **Relative path** | Relative to current directory | `logs/app.log` |
| `.` | Current directory | `cp file.txt .` |
| `..` | Parent directory | `cd ../..` |
| `~` | Current user's home | `cd ~/projects` |
| `-` | Previous directory | `cd -` |
| `/` | Root of the tree | `cd /` |

### File types (first character of `ls -l`)
| Char | Type |
|---|---|
| `-` | Regular file |
| `d` | Directory |
| `l` | Symbolic link |
| `b` | Block device (disk) |
| `c` | Character device (terminal) |
| `s` | Socket |
| `p` | Named pipe (FIFO) |

---

## 🧾 Essential Linux Commands

### 1. File & Directory Commands

| Command | Description | Example |
|---|---|---|
| `ls` | List directory contents | `ls -l /etc` |
| `cd` | Change directory | `cd /var/log` |
| `pwd` | Print working directory | `pwd` |
| `mkdir` | Make new directory | `mkdir /tmp/devops_logs` |
| `rm` | Remove files/directories | `rm -rf /tmp/devops_logs` |
| `touch` | Create a new (empty) file / update timestamp | `touch index.html` |
| `cp` | Copy files | `cp app.conf /etc/app/` |
| `mv` | Move or rename files | `mv app.log backup_app.log` |

**Important flags**
```bash
ls -l          # long listing: permissions, owner, size, mtime
ls -a          # include hidden files (dotfiles)
ls -lh         # human-readable sizes (K, M, G)
ls -ltr        # sort by modification time, newest LAST  ← great for logs
ls -la         # long + hidden (most used combo)

mkdir -p a/b/c # create nested dirs, no error if they exist
rmdir dir      # remove an EMPTY directory only

cp -r src/ dst/     # recursive (needed for directories)
cp -p file dst      # preserve permissions/timestamps
cp -a src/ dst/     # archive: recursive + preserve everything

rm -r dir      # recursive
rm -f file     # force, no prompt
rm -rf dir     # ⚠️ recursive + force — NO undo, NO recycle bin
```

> ⚠️ **`rm -rf` safety:** there is no trash can. Never run `rm -rf /` or
> `rm -rf $VAR/` when `$VAR` might be empty (it becomes `rm -rf /`). Prefer absolute paths,
> and `ls` the target first.

**Where am I / what's here — the muscle memory combo**
```bash
pwd && ls -la
```

---

### 2. File Viewing & Search

| Command | Description | Example |
|---|---|---|
| `cat` | View (concatenate) whole file content | `cat /etc/os-release` |
| `less` / `more` | View large files page by page | `less /var/log/syslog` |
| `tail` | View **end** of file | `tail -n 100 /var/log/syslog` |
| `head` | View **top** of file | `head -n 10 myfile.txt` |
| `grep` | Search **inside** files | `grep ERROR /var/log/syslog` |

**Key usage**
```bash
cat file1 file2 > merged.txt   # concatenate into a new file
cat -n file                    # with line numbers

less bigfile        # q=quit, /pattern=search, n=next match, G=end, g=start, Space=page down
                    # (less is preferred: doesn't load the whole file into memory)

head -n 20 file     # first 20 lines
tail -n 50 file     # last 50 lines
tail -f app.log     # ⭐ FOLLOW live — the #1 log-watching command
tail -F app.log     # follow even if the file is rotated/recreated
tail -100f app.log  # last 100 lines then follow
```

**`grep` — the search workhorse**
```bash
grep "ERROR" app.log              # lines containing ERROR
grep -i "error" app.log           # case-insensitive
grep -r "TODO" /app               # recursive through a directory
grep -n "ERROR" app.log           # show line numbers
grep -v "DEBUG" app.log           # INVERT: lines NOT containing DEBUG
grep -c "ERROR" app.log           # count matching lines
grep -w "up" file                 # whole word only
grep -A 5 "Exception" app.log     # 5 lines AFTER each match
grep -B 5 "Exception" app.log     # 5 lines BEFORE
grep -C 5 "Exception" app.log     # 5 lines of context both sides
grep -E "ERROR|FATAL" app.log     # extended regex (OR)
grep -ir "error" /var/log/        # ⭐ search ALL logs, case-insensitive
```

**Finding files**
```bash
find / -type f -name "file.txt"       # by name (walks the tree — accurate, slower)
find /var/log -name "*.log"           # all .log files
find /app -type d -name "node_modules"# directories only
find /var/log -size +100M             # bigger than 100 MB
find /var/log -mtime -1               # modified in the last 24 h
find /tmp -type f -mtime +7 -delete   # delete files older than 7 days
find / -type f -name "*.conf" 2>/dev/null   # hide permission-denied noise

locate file.txt      # instant, but reads a prebuilt DB — run `updatedb` first
which python3        # full path of a command found on $PATH
whereis nginx        # binary + source + man page locations
file <filename>      # identify what a file actually IS (text/ELF/gzip/...)
```

**Other text tools you will need constantly**
```bash
wc -l app.log                 # count lines
sort file | uniq -c           # count unique occurrences
cut -d':' -f1 /etc/passwd     # column 1, ':' delimited → all usernames
awk '{print $1, $9}' access.log       # print fields 1 and 9
awk '{sum+=$1} END {print sum}' nums  # sum a column
sed 's/old/new/g' file        # substitute (stream editor), print to stdout
sed -i 's/old/new/g' file     # substitute IN-PLACE (edits the file)
sed -n '10,20p' file          # print only lines 10–20
tr 'a-z' 'A-Z' < file         # translate characters
diff file1 file2              # compare two files
xargs                         # ⭐ turn stdin into command arguments
```

**Classic composition (the Unix philosophy in one line)**
```bash
# Top 10 IPs hitting an nginx log
cat access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# Delete all .tmp files found
find . -name "*.tmp" | xargs rm -f
```

---

## 👥 Users, Groups & Permissions

### User management

| Command | Description | Example |
|---|---|---|
| `adduser` | Add a new user (interactive, friendly — Debian) | `adduser devops` |
| `useradd` | Create user (non-interactive, low level) | `useradd -m -s /bin/bash devuser` |
| `usermod` | Modify a user account | `usermod -aG sudo devops` |
| `passwd` | Change a user's password | `passwd devops` |
| `id` | Display UID, GID and groups | `id devops` |
| `groups` | Show groups a user belongs to | `groups devops` |
| `deluser` / `userdel` | Delete a user | `deluser devops` / `userdel -r devops` |
| `who` | List logged-in users | `who` |
| `w` | Who is logged in **and what they're doing** | `w` |
| `last` | Login history | `last` |
| `su - user` | Switch user | `su - devops` |
| `sudo cmd` | Run one command as root | `sudo systemctl restart nginx` |
| `sudo visudo` | Safely edit the sudoers file (validates syntax) | `sudo visudo` |

**Flags worth memorising**
```bash
useradd -m devuser            # -m = create the home directory
useradd -s /bin/bash devuser  # -s = login shell
usermod -aG docker $USER      # ⭐ -aG = APPEND to Group (omitting -a REPLACES all groups!)
userdel -r olduser            # -r also removes home dir + mail spool
```

> ⚠️ `usermod -G docker user` **wipes** every other secondary group. Always use `-aG`.

**Key identity files**
| File | Contents |
|---|---|
| `/etc/passwd` | One line per user: `name:x:UID:GID:comment:home:shell` (world-readable) |
| `/etc/shadow` | Hashed passwords + ageing (root-only) |
| `/etc/group` | Group definitions and members |
| `/etc/sudoers` | Who may run what via `sudo` (edit only with `visudo`) |
| `/etc/skel/` | Template files copied into new users' home dirs |

- **UID 0 = root** (all-powerful). UID 1–999 are typically system accounts; ≥1000 are humans.
- A **nologin shell** (`/usr/sbin/nologin`) marks a service account that must not log in.

### Permissions

Every file has permissions for three classes: **user (owner)**, **group**, **others**.

```
 -rwxr-xr--  1  ashutosh  devops  4096  Sep  2 10:15  script.sh
 │└┬┘└┬┘└┬┘     └───┬──┘  └──┬─┘
 │ │  │  │          │        └── group
 │ │  │  └ others: r--        └── owner
 │ │  └── group:   r-x
 │ └───── owner:   rwx
 └─────── type: '-' regular file, 'd' directory, 'l' symlink
```

| Permission | Symbol | Numeric | On a **file** | On a **directory** |
|---|---|---|---|---|
| Read | `r` | **4** | read contents | list contents (`ls`) |
| Write | `w` | **2** | modify contents | create/delete entries inside |
| Execute | `x` | **1** | run it as a program | **enter/traverse** it (`cd`) |

**Numeric (octal) mode = sum per class**
```
7 = rwx (4+2+1)     3 = -wx        Common values:
6 = rw- (4+2)       2 = -w-          755 → rwxr-xr-x  scripts, directories, binaries
5 = r-x (4+1)       1 = --x          644 → rw-r--r--  normal files, configs
4 = r--             0 = ---          600 → rw-------  secrets, private keys ⭐
                                     700 → rwx------  private script/dir
                                     777 → rwxrwxrwx  ⚠️ NEVER in production
```

| Command | Description | Example |
|---|---|---|
| `chmod` | Change file permissions | `chmod 755 script.sh` |
| `chown` | Change file owner | `chown user:group file.txt` |
| `chgrp` | Change group only | `chgrp devops file.txt` |
| `umask` | Show/set default permission mask | `umask` |

```bash
# Numeric (absolute)
chmod 755 script.sh          # rwxr-xr-x
chmod 600 ~/.ssh/id_rsa      # ⭐ SSH refuses keys that others can read
chmod -R 755 /var/www        # recursive

# Symbolic (relative) — u=user g=group o=others a=all
chmod u+x script.sh          # add execute for owner
chmod g-w file               # remove write from group
chmod o= file                # strip all permissions from others
chmod a+r file               # everyone can read
chmod +x deploy.sh           # ⭐ make a script runnable (Session 3!)

# Ownership
chown ashutosh file.txt              # owner only
chown ashutosh:devops file.txt       # owner AND group
chown -R www-data:www-data /var/www  # recursive
```

**`umask`** — the permissions *removed* from defaults on creation.
Default files start at `666`, directories at `777`.
With `umask 022` → files become `644`, directories `755`.

**Special permission bits (good interview trivia)**
| Bit | Numeric | Effect | Example |
|---|---|---|---|
| **SUID** | `4xxx` | Run the file with the **owner's** privileges | `/usr/bin/passwd` (`-rwsr-xr-x`) |
| **SGID** | `2xxx` | Run with the group's privileges; on a dir, new files inherit its group | shared team directories |
| **Sticky** | `1xxx` | In a shared dir, only the **owner** can delete their own files | `/tmp` (`drwxrwxrwt`) |

```bash
chmod 1777 /shared    # sticky bit
chmod 4755 binary     # SUID
```

---

## ⚙️ Processes

A **process** is a running instance of a program, identified by a **PID**.

| Command | Description | Example |
|---|---|---|
| `ps` | Show processes (snapshot) | `ps aux` |
| `top` | Live list of running processes (press `q` to quit) | `top` |
| `htop` | Enhanced, interactive `top` (needs installing) | `htop` |
| `kill` | Kill a process by PID | `kill 1234` |
| `pkill` | Kill process(es) **by name** | `pkill nginx` |
| `pgrep` | Find PIDs by name | `pgrep -f python` |
| `nice` | Start a command with lower priority | `nice -n 10 backup.sh` |
| `renice` | Change priority of a running process | `renice -n -5 1234` |
| `nohup` | Run a command that survives logout | `nohup python3 app.py &` |
| `bg` / `fg` | Send a job to background / foreground | `bg`, `fg %1` |
| `jobs` | List this shell's background jobs | `jobs` |

**`ps` — the two syntaxes you'll actually type**
```bash
ps aux              # ⭐ BSD style: ALL processes, all users, with details
                    # columns: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
ps -ef              # ⭐ UNIX style: same idea (UID PID PPID C STIME TTY TIME CMD)
ps aux | grep nginx # ⭐ find a specific process
ps -ef --forest     # show the parent/child tree
ps aux --sort=-%mem | head    # top memory consumers
ps aux --sort=-%cpu | head    # top CPU consumers
```

**Process states (`STAT` column)**
| Code | Meaning |
|---|---|
| `R` | Running / runnable |
| `S` | Sleeping (interruptible) — normal for idle servers |
| `D` | Uninterruptible sleep (usually blocked on disk I/O) |
| `T` | Stopped |
| `Z` | **Zombie** — finished but its parent hasn't reaped it |

**`top` — reading the header**
```
load average: 0.52, 0.48, 0.44     ← 1/5/15-min avg runnable processes.
                                     Rule of thumb: compare against core count (`nproc`)
%Cpu(s): us=user  sy=system  id=idle  wa=IO-WAIT ⭐  st=steal (noisy VM neighbour)
KiB Mem : total, free, used, buff/cache
```
Inside `top`: `P` sort by CPU, `M` sort by memory, `k` kill a PID, `1` show per-core, `q` quit.

**Signals — `kill` is really "send a signal"**
| Signal | Number | Meaning |
|---|---|---|
| `SIGTERM` | **15** | *Please* shut down gracefully (**default** for `kill`) |
| `SIGKILL` | **9** | Force kill immediately — cannot be caught, no cleanup ⚠️ |
| `SIGHUP` | 1 | Hang up — many daemons use it to **reload config** |
| `SIGINT` | 2 | Interrupt (what `Ctrl+C` sends) |
| `SIGSTOP` | 19 | Pause the process |
| `SIGCONT` | 18 | Resume |

```bash
kill 1234           # polite SIGTERM (always try this first)
kill -9 1234        # SIGKILL — last resort, risks data loss
kill -15 1234       # explicit SIGTERM
kill -HUP 1234      # reload configuration
pkill -9 -f "python app.py"    # kill by full command line
killall nginx                  # kill all processes with that name
```

> 🧠 **Docker connection:** `docker stop` sends **SIGTERM**, waits 10 s, then sends **SIGKILL**.
> That's why apps should handle SIGTERM to shut down cleanly — and why exit code **143**
> (128+15) means "terminated" and **137** (128+9) means "killed / OOM".

**Priority:** `nice` values run **-20 (highest priority) → 19 (lowest)**. Only root can set
negative values.

---

## 🔧 Services (systemd)

A **service** (daemon) is a long-running background process — nginx, sshd, docker, mysql.
Modern Linux manages them with **systemd**, whose CLI is `systemctl`.

| Command | Description | Example |
|---|---|---|
| `systemctl status` | Check service status | `systemctl status nginx` |
| `systemctl start` | Start a service now | `systemctl start nginx` |
| `systemctl stop` | Stop it now | `systemctl stop nginx` |
| `systemctl restart` | Stop + start | `systemctl restart nginx` |
| `systemctl reload` | Re-read config **without dropping connections** | `systemctl reload nginx` |
| `systemctl enable` | Start automatically **at boot** | `systemctl enable nginx` |
| `systemctl disable` | Don't start at boot | `systemctl disable nginx` |
| `systemctl is-active` | Script-friendly check | `systemctl is-active nginx` |
| `systemctl daemon-reload` | Reload systemd after editing a unit file | `systemctl daemon-reload` |

```bash
systemctl list-units --type=service            # all loaded services
systemctl list-units --type=service --state=running
systemctl list-unit-files --state=enabled      # what starts at boot
systemctl --failed                             # ⭐ what is broken right now
systemctl cat nginx                            # show the unit file
systemctl edit nginx                           # create a drop-in override
```

> ⚠️ **`enable` ≠ `start`.** `start` affects *now*; `enable` affects *after reboot*.
> You almost always want both: `systemctl enable --now nginx`.

**Unit files** live in `/etc/systemd/system/` (your overrides) and `/lib/systemd/system/`
(package defaults). A minimal example:

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Node App
After=network.target

[Service]
User=appuser
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/node server.js
Restart=always
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
```

**Older `SysVinit` equivalents** (you'll still see these on legacy boxes):
`service nginx status`, `/etc/init.d/nginx restart`, `chkconfig nginx on`.

---

## 📦 Package Management

| OS | Command | Example |
|---|---|---|
| **Ubuntu/Debian** | Install packages | `apt update && apt install nginx -y` |
| **RHEL/CentOS** | Install packages | `yum install nginx -y` |

```bash
# ---- Debian / Ubuntu (apt) ----
apt update                    # ⭐ refresh the package index (do this FIRST)
apt upgrade -y                # upgrade installed packages
apt install nginx -y          # install
apt remove nginx              # remove binaries, keep config
apt purge nginx               # remove binaries AND config
apt autoremove                # drop orphaned dependencies
apt search nginx              # search
apt show nginx                # package details
apt list --installed          # what's installed
dpkg -l | grep nginx          # low-level query
dpkg -i package.deb           # install a local .deb

# ---- RHEL / CentOS / Amazon Linux (yum/dnf) ----
yum update -y
yum install nginx -y
yum remove nginx
yum search nginx
yum info nginx
yum list installed
rpm -qa | grep nginx          # low-level query
rpm -ivh package.rpm          # install a local .rpm

# ---- Alpine (containers!) ----
apk update
apk add --no-cache curl       # ⭐ --no-cache keeps the image small
```

> 💡 **Dockerfile connection:** always combine update+install+cleanup into **one `RUN`** so the
> cache never lands in a layer:
> ```dockerfile
> RUN apt-get update && apt-get install -y --no-install-recommends curl \
>     && rm -rf /var/lib/apt/lists/*
> ```

---

## 💾 Disk & Storage

| Command | Description | Example |
|---|---|---|
| `df` | Show disk usage of **file systems** | `df -h` |
| `du` | Show size of **files/folders** | `du -sh /var/log` |
| `lsblk` | List block devices (disks & partitions) | `lsblk` |
| `mount` / `umount` | Attach/detach a filesystem | `mount /dev/sdb1 /mnt` |
| `rsync` | Sync files/dirs (archive + compress) | `rsync -avz src/ dest/` |

```bash
df -h                     # ⭐ human-readable — first command when "disk full"
df -i                     # INODE usage — a disk can be "full" with free space
                          #   if you've created millions of tiny files!
df -hT                    # include filesystem type

du -sh /var/log           # total size of one directory
du -sh *                  # size of every item in the current dir
du -sh * | sort -h        # ⭐ sorted — find the space hog
du -h --max-depth=1 /var  # one level deep
du -ah /var/log | sort -rh | head -20   # 20 biggest files

lsblk                     # tree of disks/partitions/mountpoints
blkid                     # UUIDs (used in /etc/fstab)

mount /dev/sdb1 /mnt/data
umount /mnt/data
mount -a                  # mount everything listed in /etc/fstab

# rsync — better than cp for large/remote copies (resumable, delta transfer)
rsync -avz src/ dest/                       # -a archive, -v verbose, -z compress
rsync -avz --progress src/ user@host:/dest/ # over SSH
rsync -avz --delete src/ dest/              # make dest an exact mirror
```

> 🚨 **"No space left on device" playbook**
> 1. `df -h` → which filesystem is full?
> 2. `df -i` → is it inodes rather than bytes?
> 3. `du -sh /* 2>/dev/null | sort -h` → walk down to the culprit
> 4. Usual suspects: `/var/log` (no rotation), `/var/lib/docker` (dangling images/volumes)
> 5. Fixes: `journalctl --vacuum-time=7d`, rotate/truncate logs, `docker system prune -a`
> 6. `lsof | grep deleted` → a deleted-but-still-open file still holds space until the
>    process is restarted.

---

## 🌐 Networking Commands

| Command | Description | Example |
|---|---|---|
| `ping` | Check connectivity/reachability | `ping google.com` |
| `ip a` / `ifconfig` | Show IP / network config (`ip` is modern) | `ip a` |
| `netstat -tulnp` | List listening ports & programs | `netstat -tulnp` |
| `ss -tulnp` | Faster modern replacement for netstat | `ss -tulnp` |
| `curl` | Fetch URL data | `curl https://api.github.com` |
| `wget` | Download a file | `wget https://example.com/file.zip` |
| `nmap` | Scan open ports (needs nmap) | `nmap 10.0.0.5` |
| `traceroute` | Trace the packet path to a host | `traceroute google.com` |
| `dig` / `nslookup` | DNS lookups | `dig google.com` |
| `lsof -i :80` | See which process uses port 80 | `lsof -i :80` |
| `ethtool` | Query/control NIC driver & hardware | `ethtool -i eth0` |
| `arping` | Send ARP request to a neighbour | `arping -I eth0 192.168.1.1` |

**The flags in `ss -tulnp` / `netstat -tulnp`** (worth memorising — it's *the* port command):
```
-t  TCP        -u  UDP        -l  listening only
-n  numeric (don't resolve names — faster)     -p  show the owning process
```
```bash
ss -tulnp                 # ⭐ everything listening + which process
ss -plnt                  # listening TCP only
ss -tan                   # all TCP connections and their states
ss -tulnp | grep :8080    # who owns port 8080?
lsof -i :8080             # same question, different tool
```

**`ip` command (replaces the deprecated `ifconfig`/`route`/`arp`)**
```bash
ip a                             # all addresses (short: ip addr)
ip addr show dev eth0            # one interface
ip -s link                       # interface statistics (errors, drops)
ip r                             # routing table (short: ip route)
ip route get 8.8.8.8             # which route/interface would be used
ip neigh                         # ARP table (IP ↔ MAC neighbours)

# modifying (needs root)
ip addr add 192.168.1.10/24 dev eth0
ip addr del 192.168.1.10/24 dev eth0
ip link set eth0 up              # bring interface online
ip link set eth0 down
ip link set eth0 mtu 9000        # jumbo frames
ip route add default via 192.168.1.1 dev eth0
ip route add 192.168.1.0/24 via 192.168.1.1
ip route del 192.168.1.0/24 via 192.168.1.1
```

**net-tools → iproute2 translation table** (from the *Linux ip Command Cheat Sheet*)

| Old (net-tools) | New (iproute2) |
|---|---|
| `ifconfig -a` | `ip addr` |
| `ifconfig eth0 up` / `down` | `ip link set eth0 up` / `down` |
| `ifconfig eth0 192.168.1.1` | `ip addr add 192.168.1.1/24 dev eth0` |
| `ifconfig eth0 netmask 255.255.255.0` | `ip addr add 192.168.1.1/24 dev eth0` |
| `ifconfig eth0 mtu 9000` | `ip link set eth0 mtu 9000` |
| `ifconfig eth0:0 192.168.1.2` | `ip addr add 192.168.1.2/24 dev eth0` |
| `netstat` | `ss` |
| `netstat -neopa` | `ss -neopa` |
| `netstat -g` | `ip maddr` |
| `route` | `ip route` |
| `route add -net 192.168.1.0 netmask 255.255.255.0 dev eth0` | `ip route add 192.168.1.0/24 dev eth0` |
| `route add default gw 192.168.1.1` | `ip route add default via 192.168.1.1` |
| `arp -a` | `ip neigh` |
| `arp -v` | `ip -s neigh` |
| `arp -s 192.168.1.1 1:2:3:4:5:6` | `ip neigh add 192.168.1.1 lladdr 1:2:3:4:5:6 dev eth1` |
| `arp -i eth1 -d 192.168.1.1` | `ip neigh del 192.168.1.1 dev eth1` |

**`ss` option reference** (combinable): `-a` all sockets, `-e` detailed info, `-o` timer info,
`-n` don't resolve addresses, `-p` show owning process.

**`curl` — the API/debug tool**
```bash
curl https://api.github.com
curl -I https://example.com                    # ⭐ headers only (status, redirects)
curl -v https://example.com                    # verbose: TLS handshake, request, response
curl -L https://example.com                    # follow redirects
curl -o out.json https://api...                # save to a named file
curl -O https://example.com/file.zip           # save with the remote filename
curl -X POST -H "Content-Type: application/json" \
     -d '{"name":"test"}' http://localhost:5000/api
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health   # ⭐ health check
curl --max-time 5 http://host/                 # timeout (use in scripts!)
```

**`ethtool` (NIC-level diagnostics)**
```bash
ethtool -i eth0     # driver information
ethtool -g eth0     # ring buffer sizes
ethtool -S eth0     # network/driver statistics (drops, errors)
ethtool -p eth0     # blink the physical port LED to identify it
```

---

## 📜 Logs & Basic Troubleshooting

### Where logs live

| Path | Contents |
|---|---|
| `/var/log/syslog` | General system log (**Debian/Ubuntu**) |
| `/var/log/messages` | General system log (**RHEL/CentOS**) |
| `/var/log/auth.log` / `secure` | Authentication, sudo, SSH logins |
| `/var/log/kern.log` | Kernel messages |
| `/var/log/dmesg` | Boot-time kernel ring buffer |
| `/var/log/nginx/{access,error}.log` | Web server logs |
| `/var/log/cloud-init.log` | Cloud VM first-boot provisioning |
| `journalctl` | **systemd journal** — the unified, structured log store |

### The commands

| Command | Description |
|---|---|
| `journalctl -xe` | View critical/recent system logs with explanations |
| `tail -f /var/log/syslog` | Live-tail the system log (Debian/Ubuntu) |
| `dmesg \| less` | Kernel ring buffer (hardware, OOM killer, disk errors) |
| `strace -p PID` | Trace the **system calls** of a running process |
| `lsof -i :80` | See which process is using port 80 |
| `file <filename>` | Identify a file's type |

```bash
# ---- journalctl (systemd) ----
journalctl -u nginx                 # ⭐ logs for ONE service
journalctl -u nginx -f              # ⭐ follow live
journalctl -u nginx --since "10 min ago"
journalctl --since today --until "1 hour ago"
journalctl -p err -b                # priority error+ for the current boot
journalctl -b -1                    # the PREVIOUS boot (why did it reboot?)
journalctl -xe                      # ⭐ recent entries + explanatory hints
journalctl -k                       # kernel messages only
journalctl --disk-usage             # how much space the journal uses
journalctl --vacuum-time=7d         # ⭐ free space: keep only 7 days

# ---- classic files ----
tail -f /var/log/syslog
tail -100f /var/log/nginx/error.log
grep -i "error" /var/log/syslog | tail -50
grep -ir "error" /var/log/                  # ⭐ search ALL logs
zgrep "ERROR" /var/log/syslog.*.gz          # search ROTATED (gzipped) logs

# ---- deep debugging ----
dmesg | grep -i "oom"        # ⭐ was a process killed for memory?
dmesg -T | tail -50          # human-readable timestamps
strace -p 1234               # what syscalls is this hung process making?
strace -f -e trace=network -p 1234    # only network syscalls
lsof -p 1234                 # all files/sockets this process has open
lsof | grep deleted          # deleted files still holding disk space
```

**Log rotation** — `logrotate` (config in `/etc/logrotate.conf` + `/etc/logrotate.d/`) compresses
and deletes old logs. A server that runs out of disk from logs usually has broken rotation.

### Troubleshooting order of operations
```
1. What's the symptom?      → user report / alert / dashboard
2. Is the service running?  → systemctl status <svc> ; ps aux | grep <svc>
3. What do the logs say?    → journalctl -u <svc> -n 100 --no-pager ; tail -f /var/log/...
4. Resources OK?            → top / htop ; free -h ; df -h ; df -i
5. Network OK?              → ss -tulnp ; ping ; curl -I localhost:PORT ; dig <host>
6. Permissions OK?          → ls -l ; id ; namei -l /path/to/file
7. Config valid?            → nginx -t ; docker-compose config ; sshd -t
8. Recent change?           → git log ; ls -ltr /etc ; last ; journalctl --since <deploy time>
```

---

## ⏰ Scheduling & Background Jobs

| Command | Description | Example |
|---|---|---|
| `crontab -e` | Edit cron jobs for the current user | `crontab -e` |
| Cron syntax | Run daily at 2 AM | `0 2 * * * /home/user/backup.sh` |
| `nohup` | Run a command in the background, surviving logout | `nohup python3 app.py &` |

### Cron format
```
┌───────────── minute        (0 - 59)
│ ┌─────────── hour          (0 - 23)
│ │ ┌───────── day of month  (1 - 31)
│ │ │ ┌─────── month         (1 - 12)
│ │ │ │ ┌───── day of week   (0 - 7, 0 & 7 = Sunday)
│ │ │ │ │
* * * * *  command-to-run
```

| Schedule | Expression |
|---|---|
| Every minute | `* * * * *` |
| Every 5 minutes | `*/5 * * * *` |
| Daily at 2:00 AM | `0 2 * * *` |
| Every Sunday at midnight | `0 0 * * 0` |
| 1st of the month, 3 AM | `0 3 1 * *` |
| Weekdays at 9 AM | `0 9 * * 1-5` |
| Every 6 hours | `0 */6 * * *` |

```bash
crontab -e        # edit my crontab
crontab -l        # list my cron jobs
crontab -r        # ⚠️ REMOVE all my cron jobs
sudo crontab -u devops -l         # another user's jobs

# System-wide locations
/etc/crontab            # has an extra USER field
/etc/cron.d/            # drop-in job files
/etc/cron.{daily,hourly,weekly,monthly}/   # just drop an executable script in
```

> ⚠️ **Cron gotchas** (the classic "works manually, fails in cron"):
> - Cron has a **minimal `PATH`** — always use **absolute paths** (`/usr/bin/python3`, not `python3`).
> - Cron does **not** source `.bashrc` — export the env vars you need inside the script.
> - **Always capture output**, otherwise failures vanish:
>   `0 2 * * * /home/user/backup.sh >> /var/log/backup.log 2>&1`
> - `%` must be escaped as `\%` in crontab lines (e.g. in `date` formats).

**Background jobs**
```bash
python3 app.py &            # run in background (dies when the shell exits)
nohup python3 app.py &      # ⭐ survives logout; output → nohup.out
nohup python3 app.py > app.log 2>&1 &    # redirect output explicitly
jobs                        # list this shell's jobs
fg %1                       # bring job 1 to the foreground
bg %1                       # resume job 1 in the background
Ctrl+Z                      # suspend the foreground job
disown -h %1                # detach a job from the shell
```
For anything long-lived, prefer **`tmux`/`screen`** (a detachable terminal session) or, better,
a **systemd service**.

**Modern alternative:** `systemd` timers (`myjob.timer` + `myjob.service`) give you logging via
`journalctl`, dependency ordering and `OnBootSec`/`Persistent=true` semantics.

---

## 🖥️ System Information & Utilities

| Command | Description | Example |
|---|---|---|
| `uname -a` | Kernel & system info | `uname -a` |
| `hostname` | Show the system hostname | `hostname` |
| `uptime` | Uptime & load average | `uptime` |
| `whoami` | Current logged-in username | `whoami` |
| `history` | Show command history | `history` |
| `date` | Current system date/time | `date` |
| `clear` | Clear the terminal screen | `clear` |

```bash
uname -a                    # everything: kernel name, version, arch
uname -r                    # kernel release only (needed for driver/module work)
cat /etc/os-release         # ⭐ which distro and version
hostnamectl                 # hostname + OS + kernel + virtualisation, in one shot
uptime                      # up-time + 1/5/15-min load averages
uptime -p                   # "up 3 weeks, 2 days"
nproc                       # number of CPU cores (compare with load average!)
free -h                     # ⭐ memory usage, human-readable
lscpu                       # detailed CPU info
lsmem / cat /proc/meminfo   # memory detail
whoami / id                 # who am I, with UID/GID/groups
date; date +"%Y-%m-%d"      # now; formatted (great for log/backup filenames)
history | grep docker       # ⭐ what did I run before?
env / printenv              # all environment variables
echo $PATH                  # command search path
```

---

## 📊 Advanced Monitoring & Performance

| Command | Description |
|---|---|
| `top` | Live list of running processes (`q` to quit) |
| `htop` | Enhanced, colourful, interactive `top` (install separately) |
| `vmstat 1` | Memory, CPU and I/O usage every 1 second |
| `iostat -xz 1` | Per-device CPU & disk I/O stats per second (needs `sysstat`) |
| `uptime` | System uptime & load average |
| `free -h` | Memory usage, human-readable |
| `sar -u 1 3` | Historical/sampled CPU stats (needs `sysstat`) |
| `watch -n 1 df -h` | Re-run a command every second and show the output |

```bash
vmstat 1               # columns: r b | swpd free buff cache | si so | bi bo | in cs | us sy id wa st
                       #   r  = runnable procs waiting for CPU (persistently > cores = CPU bound)
                       #   si/so = swap in/out (non-zero = memory pressure ⚠️)
                       #   wa = CPU % waiting on I/O (high = disk bound)
iostat -xz 1           # %util near 100 and high await = saturated disk
sar -u 1 3             # CPU utilisation, 3 samples, 1 s apart
sar -r                 # memory over time
free -h                # 'available' is the number that matters, not 'free'
                       #   (Linux deliberately uses free RAM as buff/cache)
watch -n 1 'df -h'     # ⭐ refresh disk usage every second
watch -n 2 'kubectl get pods'     # very handy later
```

**Which resource is the bottleneck?**
| Symptom | Look at | Likely cause |
|---|---|---|
| High `load`, high `us` | `top`, `ps aux --sort=-%cpu` | CPU-bound application |
| High `load`, high `wa` | `iostat -xz 1`, `iotop` | Disk I/O saturation |
| High `sy` | `strace`, `dmesg` | Syscall/kernel churn, driver issue |
| `si`/`so` non-zero | `free -h`, `ps aux --sort=-%mem` | Not enough RAM → swapping |
| High `st` (steal) | cloud console | Noisy neighbour / throttled instance |

---

## 🔐 SSH & Secure File Transfer

| Command | Description |
|---|---|
| `ssh user@host` | Secure remote login |
| `scp file user@host:/path` | Secure copy over SSH |
| `rsync -avz src/ user@host:/dest/` | Efficient/resumable sync over SSH |
| `ssh-keygen` | Generate a key pair |
| `ssh-copy-id user@host` | Install your public key on a server |

```bash
ssh user@10.0.0.5
ssh -i ~/.ssh/mykey.pem ubuntu@ec2-host      # ⭐ specify an identity file
ssh -p 2222 user@host                        # non-default port
ssh user@host "df -h"                        # run one remote command and exit
ssh -L 8080:localhost:80 user@host           # local port forward (tunnel)

ssh-keygen -t ed25519 -C "ashutosh@laptop"   # modern key type
ssh-copy-id user@host                        # enable passwordless login

scp file.txt user@host:/tmp/                 # local → remote
scp user@host:/tmp/file.txt .                # remote → local
scp -r dir/ user@host:/tmp/                  # recursive
scp -i key.pem file ubuntu@host:/tmp/        # with an identity file
```

**Key files & permissions (SSH is strict — wrong modes = refused connection)**
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519          # PRIVATE key — owner read/write only
chmod 644 ~/.ssh/id_ed25519.pub      # public key
chmod 600 ~/.ssh/authorized_keys     # keys allowed to log in as this user
```
Server config: `/etc/ssh/sshd_config` (hardening: `PermitRootLogin no`,
`PasswordAuthentication no`). Validate with `sshd -t`, then `systemctl reload sshd`.

---

## ⌨️ Shortcuts & Pro Tips

| Shortcut | Description |
|---|---|
| `!!` | Run the last command again |
| `!n` | Run command number *n* from `history` |
| `Ctrl+C` | Cancel the running command |
| `Ctrl+L` | Clear the terminal screen |
| `Ctrl+R` | ⭐ Reverse-search command history |
| `Ctrl+A` / `Ctrl+E` | Jump to start / end of line |
| `Ctrl+U` / `Ctrl+K` | Delete to start / end of line |
| `Ctrl+W` | Delete the previous word |
| `Ctrl+D` | EOF / logout |
| `Ctrl+Z` | Suspend the foreground job |
| `Tab` | Auto-complete (press twice to list options) |
| `Alt+.` | Insert the last argument of the previous command |

```bash
sudo !!               # ⭐ re-run the last command with sudo (after "Permission denied")
cd -                  # jump back to the previous directory
!$                    # last argument of the previous command
mkdir -p /a/b && cd $_    # $_ = last argument
alias ll='ls -alF'    # ⭐ handy shortcut (put it in ~/.bashrc to persist)
tldr tar              # simplified, example-first man pages (install: npm i -g tldr)
man ls / ls --help    # the built-in documentation
type ll               # is it an alias, function, or binary?
```

**Pro tips from the advanced cheat sheet**
```bash
watch -n 1 df -h                 # refresh disk usage every second
ss -plnt                         # open listening ports + owning processes
history | grep ssh               # find that ssh command you used last week
uptime && who                    # uptime and who is logged in
netstat -plant | grep :22        # connections on port 22
ls -ltr                          # list by modified time, latest LAST ⭐ (newest at the bottom)
grep -ir "error" /var/log/       # search all logs for "error", case-insensitive
xargs                            # run commands built from stdin (great for cleanup)
alias ll='ls -alF'               # create handy shell shortcuts
```

**Persisting your setup:** put aliases/exports in `~/.bashrc` (interactive shells) and reload
with `source ~/.bashrc`.

---

## 🩺 Troubleshooting Playbook

| Problem | Diagnose with |
|---|---|
| **Service won't start** | `systemctl status X` → `journalctl -u X -n 50 --no-pager` → config test (`nginx -t`) → is the port already taken (`ss -tulnp`)? |
| **Port already in use** | `ss -tulnp \| grep :8080`, `lsof -i :8080` → `kill` the owner or change the port |
| **Disk full** | `df -h` → `df -i` → `du -sh /* \| sort -h` → `journalctl --vacuum-time=7d`, `docker system prune -a` |
| **High CPU** | `top` (press `P`) → `ps aux --sort=-%cpu \| head` → `strace -p PID` |
| **High memory / OOM kills** | `free -h` → `ps aux --sort=-%mem \| head` → `dmesg \| grep -i oom` |
| **Slow disk** | `iostat -xz 1` (`%util`, `await`) → `iotop` |
| **Can't reach a host** | `ping <ip>` (network) → `ping <name>` (DNS) → `dig <name>` → `traceroute` → `curl -v` |
| **Permission denied** | `ls -l` the file → `id` yourself → `namei -l /full/path` (check every parent dir has `x`) |
| **Command not found** | `echo $PATH`, `which`/`whereis`, is the package installed? |
| **Process is hung** | `ps aux \| grep X` (`STAT` = `D` means blocked on I/O) → `strace -p PID` → `lsof -p PID` |
| **Ran out of inodes** | `df -i` → `find /path -xdev -type f \| wc -l` → delete masses of small files |
| **Something changed** | `ls -ltr /etc`, `journalctl --since "1 hour ago"`, `last`, `history` |

---

## 🔗 References
- Linux `ip` command cheat sheet — http://www.LinuxTrainingAcademy.com
- `man` pages: `man ls`, `man 7 signal`, `man 5 crontab`
- `tldr` — https://tldr.sh
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
