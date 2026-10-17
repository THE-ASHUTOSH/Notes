# ⚡ S02 · Linux Fundamentals

> *Revision card.* Full notes → [Session 2](../02_Linux_Fundamentals.md)

---

## 🔑 One-line core

***`/etc` = config · `/var/log` = logs · `/var/lib` = state.*** Those three answer most
"where is it?" questions — and come back as Docker volume mounts.

---

## 📂 FHS — the only dirs you need

| Path | Holds |
|---|---|
| `/etc` | configuration |
| `/var/log` | logs |
| `/var/lib` | application state (`/var/lib/docker`, `/var/lib/mysql`) |
| `/usr/bin`, `/bin` | binaries |
| `/home` | users |
| `/tmp` | scratch (sticky bit) |
| `/proc`, `/sys` | kernel, as files |
| `/dev` | devices |

---

## 🔐 Permissions — the arithmetic

```
r = 4     w = 2     x = 1
          owner | group | other
  755  =   rwx  |  r-x  |  r-x
  644  =   rw-  |  r--  |  r--
  600  =   rw-  |  ---  |  ---   ← keys, .env
```

| Command | Does |
|---|---|
| `chmod +x f` | make executable |
| `chown u:g f` | change owner |
| `umask` | default-permission mask |
| SUID / sticky | run-as-owner / only-owner-deletes |

---

## ⚡ Signals

| № | Signal | |
|---|---|---|
| 2 | `SIGINT` | Ctrl-C |
| 9 | `SIGKILL` | **cannot be caught** |
| 13 | `SIGPIPE` | write to closed peer |
| 15 | `SIGTERM` | the polite kill |

> ⭐ *SIGTERM asks, SIGKILL forces.* → `docker stop` = **143**, `docker kill` = **137**.

---

## 🔧 systemd

```bash
systemctl status|start|stop|restart|enable <svc>
journalctl -u <svc> -f          # ← follow its logs
journalctl --since "1 hour ago"
```

> ⭐ **`systemctl status` → `journalctl -u` is the start of every investigation.**

---

## 🧾 Commands worth muscle memory

```bash
grep -rn "text" .        find . -name "*.log" -mtime +7
tail -f app.log          less +F app.log
ps aux | grep X          top / htop
df -h   (space)          df -i   (inodes!)
du -sh *                 lsof -i :8080
netstat -tulpn / ss -ltnp
```

---

## 📦 Package managers

| Distro | Tool |
|---|---|
| Debian/Ubuntu | `apt` |
| RHEL/CentOS | `yum` / `dnf` |
| **Alpine** | `apk` ← tiny base images |

---

## ⚠️ Traps

- **Two disk failures:** no space (`df -h`) **and** no inodes (`df -i`). Check both.
- `command not found` → `echo $PATH`, `which`
- `permission denied` → `ls -l`, `chmod +x`
- CRLF line endings break `.sh` on Linux (`bad interpreter: ^M`)

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| Service won't start, first 2 commands? | `systemctl status` → `journalctl -u` |
| Disk full but `df -h` says free? | out of **inodes** |
| 755 vs 644? | executable vs read-only-for-others |
| Why is a container "just Linux"? | namespaces (what it *sees*) + cgroups (what it *gets*) |

---

⬅️ [S01](./01_DevOps_and_Microservices.md) · ➡️ [S03 · Shell](./03_Shell_Scripting.md)
