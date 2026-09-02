# Session 3 — Shell Scripting 🐚

> A shell script is just **the commands you already type, saved in a file** so a machine can run
> them the same way every time. This is the first real *automation* skill in DevOps: health checks,
> log cleanup, backups, deployment steps, container entrypoints and CI steps are all shell.

---

## 📑 Table of Contents
1. [What & Why](#-what-is-shell-scripting)
2. [Anatomy of a Script](#-anatomy-of-a-script)
3. [Variables](#-variables)
4. [Taking Input](#-taking-input-read)
5. [Command Substitution](#-command-substitution)
6. [Arguments](#-arguments-cli-parameters)
7. [Conditions](#-conditions)
8. [Loops](#-loops)
9. [Functions](#-functions)
10. [Pipes & Redirection](#-pipes--redirection)
11. [Arrays](#-arrays)
12. [Exit Codes & Error Handling](#-exit-codes--error-handling)
13. [Debugging Scripts](#-debugging-scripts)
14. [Worked Examples from Class](#-worked-examples-from-class)
15. [Practical Automation Scripts](#-practical-automation-scripts)
16. [Best Practices](#-best-practices)
17. [Cheat Sheet](#-quick-cheat-sheet)

---

## 🎯 What is Shell Scripting?

A **shell script** is a plain-text file containing a sequence of shell commands, executed
top-to-bottom by an interpreter (usually **bash**).

**Why DevOps engineers live in shell:**
| Use case | Example |
|---|---|
| **Automation of repetitive tasks** | Rotate logs, clean temp files, restart a stuck service |
| **Deployment steps** | Pull image → stop old container → start new → health check |
| **CI/CD glue** | Every `run:` step in GitHub Actions is a shell command |
| **Container entrypoints** | `entrypoint.sh` that waits for the DB then starts the app |
| **Health checks & monitoring** | Curl an endpoint, check exit code, alert |
| **Backups** | `tar` + `aws s3 cp` + delete-older-than-N-days |
| **Bootstrapping servers** | Cloud `user-data` scripts on first boot |

**Shell vs Python:** use **shell** when the job is mostly *calling other programs and moving files*.
Switch to **Python** when you need real data structures, JSON/API parsing, or the script grows past
~150 lines.

**Shell types**
| Shell | Notes |
|---|---|
| `sh` (POSIX/dash) | Minimal, most portable. **Alpine containers only have `sh`** — no `[[ ]]`, no arrays. |
| `bash` | The default on most Linux distros; the one we write for. |
| `zsh` | Common on macOS, interactive-friendly. |

---

## 🧱 Anatomy of a Script

```bash
#!/bin/bash
# ^ SHEBANG — tells the OS which interpreter to use

# 1. Make it executable, then run it
```

```bash
chmod +x hello.sh     # ⭐ grant execute permission (Session 2!)
./hello.sh            # run it (./ = "in this directory")

# other ways to run:
bash hello.sh         # explicit interpreter (shebang not required)
sh hello.sh           # POSIX mode
source hello.sh       # ⭐ run in the CURRENT shell — variables persist afterwards
. hello.sh            # same as source
```

**The shebang matters**
| Line | Meaning |
|---|---|
| `#!/bin/bash` | Use bash at that exact path (fine on Linux) |
| `#!/usr/bin/env bash` | Find bash on `$PATH` — **more portable** (works on macOS/BSD) |
| `#!/bin/sh` | POSIX shell — maximum portability, fewer features |
| `#!/usr/bin/python3` | Scripts don't have to be shell! |

**Comments:** `#` to end of line. There is no block comment (use `#` on each line).

**A well-formed script skeleton:**
```bash
#!/usr/bin/env bash
#
# backup.sh — archive /app and upload to S3
# Usage: ./backup.sh <target-dir>

set -euo pipefail          # ⭐ safety flags (explained later)

readonly LOG="/var/log/backup.log"
TARGET="${1:-/app}"

main() {
  echo "[$(date '+%F %T')] backing up ${TARGET}"
  # ...
}

main "$@"
```

---

## 📦 Variables

### Declaring and using
```bash
#!/bin/bash

variable="Hello, World!"
echo $variable
```

**Rules — the ones that actually bite you:**
```bash
name="Nensi"            # ✅ NO SPACES around '='
name = "Nensi"          # ❌ bash reads this as: run command `name` with args `=` and `"Nensi"`
name= "Nensi"           # ❌ also wrong

roll_no=123             # ✅ no type declaration — everything is a string
comment="Awesome"

echo "My name is $name"          # ✅ double quotes: variables EXPAND
echo 'My name is $name'          # ❌ single quotes: literal → prints $name
echo "My name is ${name}"        # ⭐ braces: safest, required when concatenating
echo "${name}_backup.tar.gz"     # without braces, bash would look for $name_backup
```

> ⚠️ **Do not use command names as variable names.**
> ```bash
> ls="myfile"      # ❌ wrong way — shadows/confuses the `ls` command
> ```
> Use descriptive names instead: `log_file="myfile"`.

### Naming conventions
| Convention | Use |
|---|---|
| `lower_snake_case` | Local script variables |
| `UPPER_SNAKE_CASE` | Environment variables & constants (`APP_ENV`, `MAX_RETRIES`) |
| `readonly PI=3.14` | Constants that must not change |
| `local x=1` | Variables **inside a function** (always do this!) |

### Quoting rules (the #1 source of bugs)
| Form | Behaviour |
|---|---|
| `"$var"` | Expands the variable, **preserves spaces** — ⭐ use this by default |
| `'$var'` | Literal `$var`, no expansion |
| `$var` | Expands but **word-splits** — breaks on filenames with spaces |
| `` `cmd` `` / `$(cmd)` | Runs the command and substitutes its output |
| `\$` | Escaped literal `$` |

```bash
file="my report.txt"
rm $file       # ❌ tries to remove 'my' AND 'report.txt'
rm "$file"     # ✅ correct
```

### Environment vs shell variables
```bash
MY_VAR="local"          # shell variable — only this shell sees it
export MY_VAR="shared"  # ⭐ environment variable — CHILD processes inherit it
env | grep MY_VAR       # list environment variables
unset MY_VAR            # delete it
```

### Useful built-in variables
| Variable | Meaning |
|---|---|
| `$HOME` | Current user's home directory |
| `$USER` | Current username |
| `$PWD` | Current working directory |
| `$PATH` | Where the shell looks for commands |
| `$HOSTNAME` | Machine name |
| `$RANDOM` | A random number |
| `$$` | PID of the current shell |
| `$?` | ⭐ Exit status of the last command |
| `$0` | Script name |
| `$#` | Number of arguments |
| `$@` / `$*` | All arguments |

### Parameter expansion (very handy)
```bash
${VAR:-default}       # ⭐ use "default" if VAR is unset/empty (does NOT assign)
${VAR:=default}       # use AND assign the default
${VAR:?error msg}     # abort with an error if VAR is unset ⭐ great for required config
${#VAR}               # length of the value
${VAR^^}              # uppercase       ${VAR,,} = lowercase
${VAR/old/new}        # replace first occurrence   (//  = replace all)
${VAR#prefix}         # strip shortest matching prefix   (##  = longest)
${VAR%suffix}         # strip shortest matching suffix   (%%  = longest)

file="app.tar.gz"
echo "${file%.*}"     # app.tar     (drop last extension)
echo "${file%%.*}"    # app         (drop all extensions)
echo "${file##*.}"    # gz          (get the extension)

PORT="${PORT:-8080}"                  # ⭐ classic config-with-default pattern
DB_PASS="${DB_PASS:?DB_PASS required}" # fail fast if a secret is missing
```

---

## ⌨️ Taking Input (`read`)

`input.sh` — from class:
```bash
#!/bin/bash

read -p "Enter your name: " name
read -p "Enter your roll number: " roll_no
read -p "Enter your comment: " comment

echo  "My name is $name"
echo "My roll number is $roll_no"
echo "My comment is: $comment"
```

**`read` options**
```bash
read -p "Prompt: " var        # ⭐ -p shows a prompt on the same line
read -s -p "Password: " pass  # ⭐ -s silent (don't echo) — for secrets
read -t 10 -p "Quick! " var   # -t timeout in seconds
read -n 1 -p "Continue? " ch  # -n read only N characters
read -r line                  # ⭐ -r raw: don't interpret backslashes (best practice)
read a b c                    # split one line into several variables
read -a arr                   # read a line into an array

# read a file line by line — the correct idiom
while IFS= read -r line; do
  echo "Line: $line"
done < input.txt
```

> 💡 `read` blocks waiting for a human. **Never use it in CI or a container entrypoint** — use
> arguments or environment variables there instead.

---

## 🔁 Command Substitution

Capture the **output of a command** into a variable.

`task.md` / `test1.sh` pattern from class:
```bash
current_date=$(date)
echo $current_date
```

```bash
current_date=$(date)                  # ⭐ modern, nestable — PREFER THIS
current_date=`date`                   # legacy backticks — works, but don't nest

# useful captures
today=$(date +%Y-%m-%d)               # 2026-09-03
stamp=$(date +%Y%m%d_%H%M%S)          # 20260903_101530  ⭐ perfect for filenames
host=$(hostname)
me=$(whoami)
count=$(ls -1 | wc -l)
free_pct=$(df -h / | awk 'NR==2 {print $5}')
ip=$(hostname -I | awk '{print $1}')

echo "Backup started on $host by $me at $current_date"
tar -czf "backup_${stamp}.tar.gz" /app     # ⭐ timestamped backup
```

> ⚠️ **Class gotcha:** in `task.md` you'll see
> ```bash
> echo $hostname     # prints NOTHING — $hostname is an undefined variable
> echo $whoami       # prints NOTHING
> ```
> These are **commands, not variables**. The correct forms are:
> ```bash
> echo "$(hostname)"     # or just: hostname
> echo "$(whoami)"       # or just: whoami
> ```
> (Bash does happen to define `$HOSTNAME` and `$USER`, but `$hostname`/`$whoami` are not variables.)

**Arithmetic**
```bash
count=5
echo $((count + 1))          # ⭐ arithmetic expansion → 6
((count++))                  # increment in place
total=$((price * qty))
result=$(echo "scale=2; 10/3" | bc)   # floating point needs `bc`
```

---

## 🎛️ Arguments (CLI parameters)

Arguments make a script **reusable and CI-friendly** (no interactive prompts).

| Variable | Meaning |
|---|---|
| `$0` | Script name |
| `$1`, `$2`, … `${10}` | First, second, … tenth argument |
| `$#` | ⭐ Number of arguments |
| `$@` | All arguments as **separate** words — ⭐ always quote: `"$@"` |
| `$*` | All arguments as **one** string |
| `$?` | Exit code of the last command |
| `$$` | PID of this script |
| `shift` | Drop `$1`; everything shifts left |

```bash
#!/bin/bash
# Usage: ./deploy.sh <environment> <version>

if [ $# -ne 2 ]; then
  echo "Usage: $0 <environment> <version>"
  exit 1
fi

ENV="$1"
VERSION="$2"

echo "Script name : $0"
echo "Environment : $ENV"
echo "Version     : $VERSION"
echo "Arg count   : $#"
echo "All args    : $@"
```
```bash
chmod +x deploy.sh
./deploy.sh staging 1.4.2
```

**Looping over arguments**
```bash
for arg in "$@"; do
  echo "Processing $arg"
done
```

**Parsing flags with `getopts`** (for real tools)
```bash
#!/bin/bash
while getopts "e:v:h" opt; do
  case $opt in
    e) ENV="$OPTARG" ;;
    v) VERSION="$OPTARG" ;;
    h) echo "Usage: $0 -e <env> -v <version>"; exit 0 ;;
    *) echo "Invalid option"; exit 1 ;;
  esac
done
echo "Deploying $VERSION to $ENV"
# ./deploy.sh -e prod -v 2.0.1
```

---

## 🔀 Conditions

### `if / elif / else` — the class example (`condition.sh`)
```bash
#!/bin/bash

read -p "Enter your age: " age

if [ $age -lt 0 ]; then
    echo "Invalid age. Please enter a valid age."
elif [ $age -lt 13 ]; then
    echo "You are a child."
elif [ $age -lt 20 ]; then
    echo "You are a teenager."
else
    echo "You are an adult."
fi
```

**Syntax rules that trip everyone up:**
```bash
if [ "$a" -eq "$b" ]; then    # ⭐ SPACES are mandatory inside [ ]
if [$a -eq $b]; then          # ❌ "[: command not found"  — [ is a COMMAND
fi                            # every `if` closes with `fi`
then                          # needs `;` before it on the same line, or its own line
```

### Numeric comparisons (integers)
| Operator | Meaning |
|---|---|
| `-eq` | equal |
| `-ne` | not equal |
| `-lt` | less than |
| `-le` | less than or equal |
| `-gt` | greater than |
| `-ge` | greater than or equal |

### String comparisons
| Operator | Meaning |
|---|---|
| `=` or `==` | equal |
| `!=` | not equal |
| `-z "$s"` | ⭐ string is **empty** (zero length) |
| `-n "$s"` | string is **not** empty |
| `<` / `>` | lexicographic (use inside `[[ ]]`) |

### File tests (essential for DevOps scripts)
| Test | True when |
|---|---|
| `-f file` | ⭐ exists and is a **regular file** |
| `-d dir` | ⭐ exists and is a **directory** |
| `-e path` | exists (any type) |
| `-s file` | exists and is **non-empty** |
| `-r` / `-w` / `-x` | readable / writable / executable |
| `-L file` | is a symbolic link |
| `f1 -nt f2` | f1 is newer than f2 |

### Logical operators
```bash
if [ "$a" -gt 0 ] && [ "$b" -gt 0 ]; then ...   # ⭐ AND (preferred form)
if [ "$a" -gt 0 ] || [ "$b" -gt 0 ]; then ...   # OR
if [ ! -f /etc/app.conf ]; then ...             # NOT
if [ "$a" -gt 0 -a "$b" -gt 0 ]; then ...       # legacy -a / -o (avoid)
```

### `[ ]` vs `[[ ]]`
| | `[ ]` (POSIX `test`) | `[[ ]]` (bash keyword) |
|---|---|---|
| Portability | Works in `sh` (**Alpine!**) | bash/zsh only |
| Word splitting | Happens — must quote | Doesn't — safer |
| Regex | No | ✅ `=~` |
| Pattern match | No | ✅ `==` with globs |
| `&&` / `\|\|` inside | No | ✅ Yes |

```bash
# From while_loop.sh in class:
if [[ $input == "q" ]]; then ...              # string compare inside [[ ]]
elif ! [[ $input =~ ^[0-9]+$ ]]; then ...     # ⭐ REGEX match — is it all digits?

[[ "$file" == *.log ]]         # glob pattern matching
[[ "$v" =~ ^v[0-9]+\.[0-9]+$ ]] # regex
(( count > 5 ))                 # ⭐ arithmetic context — no $ needed, C-style operators
```

### `case` — cleaner than a long `elif` chain
```bash
case "$1" in
  start)         systemctl start myapp ;;
  stop)          systemctl stop myapp ;;
  restart)       systemctl restart myapp ;;
  status)        systemctl status myapp ;;
  prod|staging)  echo "Deploying to $1" ;;      # multiple patterns
  *.log)         echo "That's a log file" ;;    # glob patterns work
  *)             echo "Usage: $0 {start|stop|restart|status}"; exit 1 ;;
esac
```

### One-liner conditionals
```bash
[ -f config.yml ] && echo "found"                  # run if true
[ -f config.yml ] || echo "missing"                # run if false
[ -d /backup ] || mkdir -p /backup                 # ⭐ create-if-absent idiom
command -v docker >/dev/null 2>&1 || { echo "docker not installed"; exit 1; }
```

---

## 🔄 Loops

### `for` loop over a range — class example (`loop.sh`)
```bash
#!/bin/bash
# for in in 1 2 3 4 5

for i in {1..5}
do
  echo "This is iteration number $i"
done
```

**All the `for` forms**
```bash
for i in 1 2 3 4 5;    do echo "$i"; done      # explicit list
for i in {1..5};       do echo "$i"; done      # ⭐ brace range
for i in {1..10..2};   do echo "$i"; done      # step of 2 → 1 3 5 7 9
for i in $(seq 1 5);   do echo "$i"; done      # using seq
for ((i=0; i<5; i++)); do echo "$i"; done      # ⭐ C-style
for f in *.log;        do echo "$f"; done      # ⭐ glob over files
for f in /var/log/*.log; do gzip "$f"; done
for svc in nginx docker sshd; do systemctl status "$svc"; done   # list of names
for arg in "$@";       do echo "$arg"; done    # over script arguments
for line in $(cat hosts.txt); do ssh "$line" uptime; done        # (see caveat below)
```

> ⚠️ `for line in $(cat file)` splits on **whitespace**, not lines. To iterate real lines use
> `while IFS= read -r line; do ...; done < file`.

### `while` loop with a counter — class example (`while_loop1.sh`)
```bash
#!/bin/bash

count=0
while [ $count -lt 5 ]
do
  echo "This is iteration number $count"
  ((count++))
done
```

### `while true` + `break` / `continue` — class example (`while_loop.sh`)
```bash
#!/bin/bash

while true; do
    read -p "Enter a number (or 'q' to quit): " input

    if [[ $input == "q" ]]; then
        echo "Exiting the loop."
        break                 # ⭐ leave the loop entirely
    elif ! [[ $input =~ ^[0-9]+$ ]]; then
        echo "Invalid input. Please enter a valid number."
        continue              # ⭐ skip to the next iteration
    fi

    echo "You entered: $input"
done
```

This tiny script demonstrates four important ideas at once:
1. **Infinite loop** (`while true`) driven by user input
2. **`break`** — exit condition
3. **`continue`** — input validation without exiting
4. **Regex validation** `^[0-9]+$` (`^`=start, `[0-9]+`=one or more digits, `$`=end)

### `until` loop (runs *until* the condition becomes true)
```bash
# ⭐ Very common in containers: wait for a dependency to come up
until curl -sf http://database:3306 >/dev/null 2>&1; do
  echo "Waiting for database..."
  sleep 2
done
echo "Database is ready!"
```

### Reading a file line by line
```bash
while IFS= read -r line; do
  echo "Processing: $line"
done < servers.txt
```
- `IFS=` prevents leading/trailing whitespace from being stripped
- `-r` prevents backslash interpretation

### Loop control
| Keyword | Effect |
|---|---|
| `break` | Exit the loop |
| `break 2` | Exit two levels of nested loops |
| `continue` | Skip to the next iteration |
| `sleep N` | Pause N seconds (essential in retry/wait loops) |

---

## 🧩 Functions

Class example (`function.sh`):
```bash
#!/bin/bash

show_info(){
  echo "This is a function"
  echo "This is a function to show information"
}

show_info()      # ❌ BUG — see below
```

> ⚠️ **Fix the class bug:** you **define** a function with `name() { ... }` but you **call** it
> with just its **name — no parentheses**:
> ```bash
> show_info        # ✅ correct call
> show_info()      # ❌ this RE-DECLARES the function (and is a syntax error here)
> ```

### Correct version
```bash
#!/bin/bash

show_info() {
  echo "This is a function"
  echo "This is a function to show information"
}

show_info          # ✅ call it
```

### Functions with arguments and return values
```bash
#!/bin/bash

# Arguments inside a function work exactly like script arguments: $1 $2 $# $@
greet() {
  local name="$1"          # ⭐ ALWAYS use `local` — otherwise variables are global
  local greeting="${2:-Hello}"
  echo "$greeting, $name!"
}

greet "Ashutosh"           # → Hello, Ashutosh!
greet "Ashutosh" "Welcome" # → Welcome, Ashutosh!

# --- Returning a STATUS (0 = success) ---
is_service_running() {
  systemctl is-active --quiet "$1"    # exit code becomes the function's status
}

if is_service_running nginx; then
  echo "nginx is up"
else
  echo "nginx is DOWN"
fi

# --- Returning a VALUE: echo it and capture with $( ) ---
get_timestamp() {
  echo "$(date +%Y%m%d_%H%M%S)"
}
stamp=$(get_timestamp)

# --- `return` only returns an exit code 0-255, NOT data ---
add() { return $(( $1 + $2 )); }
add 3 4; echo "$?"    # 7  (works, but abuse — use echo for real values)
```

**Reusable helpers you'll write in every script:**
```bash
log()  { echo "[$(date '+%F %T')] $*"; }
warn() { echo "[$(date '+%F %T')] WARN: $*" >&2; }
die()  { echo "[$(date '+%F %T')] ERROR: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is not installed"
}

log "Starting deployment"
require_cmd docker
[ -f app.conf ] || die "app.conf missing"
```

**Function rules**
- Must be **defined before** it is called (scripts run top-to-bottom).
- Both `function name { }` and `name() { }` work — `name() { }` is more portable.
- Variables are **global by default** → use `local` inside functions.

---

## 🚰 Pipes & Redirection

### Streams
| Stream | FD | Purpose |
|---|---|---|
| `stdin` | **0** | Input |
| `stdout` | **1** | Normal output |
| `stderr` | **2** | ⭐ Error output (separate on purpose!) |

### Redirection
```bash
command > file        # ⭐ redirect stdout, OVERWRITE the file
command >> file       # ⭐ redirect stdout, APPEND
command 2> file       # redirect stderr only
command 2>> file      # append stderr
command > out 2> err  # separate files
command > file 2>&1   # ⭐ BOTH stdout and stderr into one file (order matters!)
command &> file       # bash shorthand for the same
command < input.txt   # feed a file in as stdin
command > /dev/null   # discard output
command 2>/dev/null   # ⭐ discard errors only (hide "Permission denied" noise)
command &> /dev/null  # discard everything
```

> ⚠️ `2>&1` means "send stderr wherever stdout is *currently* going", so
> `cmd > file 2>&1` ✅ works, but `cmd 2>&1 > file` ❌ leaves stderr on the terminal.

**Class examples**
```bash
# from data.sh — > OVERWRITES
echo "This is a log file." > app.log
cat app.log                        # This is a log file.
echo "This is my file" > app.log   # overwrites!
cat app.log                        # This is my file

# from script1.sh — >> APPENDS
echo "this is file1" > app.log     # creates/overwrites
echo "this is file2" >> app.log    # appends a second line
cat app.log                        # this is file1
                                   # this is file2

# from task.md — capture command output into a file
ps > process.log
```

### Pipes `|`
Send the **stdout of one command into the stdin of the next** — the heart of the Unix philosophy.

```bash
ps aux | grep nginx                          # ⭐ find a process
cat app.log | grep ERROR | wc -l             # count error lines
ls -l | less                                 # page through long output
docker ps -q | xargs docker stop             # ⭐ xargs: turn stdin into ARGUMENTS
cat access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
du -sh * | sort -h                           # find the biggest directory
history | grep docker
journalctl -u nginx | grep -i error | tail -20
```

**`|` vs `xargs`:** a pipe feeds data to a command's **stdin**; `xargs` converts that data into
**command-line arguments**. `rm` doesn't read stdin, so you need `xargs`:
```bash
find . -name "*.tmp" | xargs rm -f
find . -name "*.tmp" -print0 | xargs -0 rm -f    # safe with spaces in filenames
```

**Other operators**
```bash
cmd1 && cmd2       # ⭐ run cmd2 ONLY if cmd1 succeeded (exit 0)
cmd1 || cmd2       # run cmd2 only if cmd1 FAILED
cmd1 ; cmd2        # run both regardless
cmd &              # run in the background
cmd1 | tee out.txt # ⭐ show output on screen AND write to a file
cmd1 | tee -a out.txt   # tee in append mode
```

**Here-document / here-string** (feed a block of text as stdin)
```bash
cat > config.yml <<EOF          # variables ARE expanded
app: myapp
port: ${PORT}
EOF

cat > config.yml <<'EOF'        # ⭐ quoted delimiter → NO expansion (literal)
app: myapp
port: ${PORT}
EOF

grep "x" <<< "$my_string"       # here-string
```

---

## 📚 Arrays

```bash
# Indexed arrays (bash, not POSIX sh)
servers=("web01" "web02" "db01")

echo "${servers[0]}"        # web01     (first element — 0-indexed)
echo "${servers[@]}"        # all elements
echo "${#servers[@]}"       # 3         (count)
echo "${servers[@]:1:2}"    # web02 db01  (slice)

servers+=("cache01")        # append

for s in "${servers[@]}"; do
  echo "Checking $s"
done

# Associative arrays (bash 4+) — like a dict/map
declare -A ports
ports[web]=80
ports[api]=5000
echo "${ports[api]}"                 # 5000
for k in "${!ports[@]}"; do          # ! gives KEYS
  echo "$k → ${ports[$k]}"
done

# Split a string into an array
IFS=',' read -ra parts <<< "a,b,c"
echo "${parts[1]}"                   # b
```

---

## 🚦 Exit Codes & Error Handling

### Exit codes
Every command returns an integer: **0 = success**, non-zero = failure.

```bash
ls /nonexistent
echo $?          # ⭐ 2 (non-zero → it failed)

grep "x" file; echo $?    # 0 = found, 1 = not found

exit 0           # end the script successfully
exit 1           # end with a generic error
```

| Code | Conventional meaning |
|---|---|
| `0` | Success |
| `1` | General error |
| `2` | Misuse of a shell builtin / bad arguments |
| `126` | Command found but **not executable** (permissions) |
| `127` | ⭐ **Command not found** (typo / missing PATH) |
| `128+N` | Killed by signal N → **130** = Ctrl+C (SIGINT), **137** = SIGKILL/OOM, **143** = SIGTERM |

> 💡 These are the **same codes you read from `docker ps -a`** when a container exits.
> `137` almost always means the container was OOM-killed.

### The safety flags — put these at the top of every serious script
```bash
set -e            # ⭐ exit immediately if any command fails
set -u            # ⭐ error on use of an UNDEFINED variable (catches typos)
set -o pipefail   # ⭐ a pipeline fails if ANY stage fails (not just the last)
set -x            # print each command before running it (debugging)

set -euo pipefail # ⭐⭐ the standard one-liner
IFS=$'\n\t'       # safer word splitting (Bash "strict mode")
```

Without `set -e`, a failing step is silently ignored and the script marches on — which in a deploy
script means **deploying a broken build**.

### `trap` — cleanup on exit
```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT       # ⭐ always clean up, however we exit
trap 'echo "Interrupted!"; exit 130' INT TERM

# ... work inside $tmpdir ...
```

### Explicit error checks
```bash
if ! docker build -t myapp .; then
  echo "Build failed" >&2
  exit 1
fi

command -v kubectl >/dev/null 2>&1 || { echo "kubectl missing" >&2; exit 1; }

mkdir -p /backup || { echo "cannot create /backup" >&2; exit 1; }
```

### Retry with backoff (a genuinely useful pattern)
```bash
retry() {
  local n=1 max=5 delay=5
  until "$@"; do
    if (( n >= max )); then
      echo "Command failed after $n attempts: $*" >&2
      return 1
    fi
    echo "Attempt $n/$max failed. Retrying in ${delay}s..."
    sleep "$delay"; ((n++))
  done
}

retry curl -sf https://api.example.com/health
```

---

## 🐞 Debugging Scripts

```bash
bash -n script.sh      # ⭐ syntax check ONLY, don't execute (dry run)
bash -x script.sh      # ⭐ trace: print every command with expanded variables
bash -v script.sh      # print each line as read
set -x  ...  set +x    # trace just one section of a script

# Nicer trace output: show file + line number
export PS4='+ ${BASH_SOURCE}:${LINENO}: '
bash -x script.sh
```

**`shellcheck`** — the linter every shell script should pass. It catches unquoted variables,
useless `cat`, wrong test operators and dozens of real bugs:
```bash
shellcheck script.sh
```

**Debug checklist**
| Symptom | Likely cause |
|---|---|
| `Permission denied` | Forgot `chmod +x` |
| `command not found` (127) | Typo, or not on `$PATH` (esp. in cron) |
| `[: command not found` | Missing spaces inside `[ ]` |
| `unexpected end of file` | Unclosed `if`/`fi`, `do`/`done`, or quote |
| Variable is empty | Typo, or set inside a subshell/pipe, or not `export`ed |
| `bad interpreter: ^M` | ⭐ **Windows CRLF line endings** → `dos2unix script.sh` |
| Works manually, fails in cron | Different `PATH`/env; use absolute paths |

> 🪟 **Windows users:** editing a `.sh` file in a Windows editor can save CRLF (`\r\n`) endings,
> which Linux reads as part of the command. Fix with `dos2unix script.sh` or
> `sed -i 's/\r$//' script.sh`, and set `git config core.autocrlf input`.

---

## 🧪 Worked Examples from Class

### 1. `hello.sh` — create a dir, a file, write and read it
```bash
mkdir hello
cd hello
touch app.log
echo "This is my logfile" > app.log
cat app.log
```
Teaches: `mkdir`, `cd`, `touch`, `>` redirect, `cat`.

### 2. `data.sh` — overwrite behaviour of `>`
```bash
mkdir data1
cd data1
echo "This is a log file." > app.log
cat app.log
echo "This is my file" > app.log     # ⭐ OVERWRITES the previous content
cat app.log
```

### 3. `script1.sh` — append behaviour of `>>`
```bash
mkdir test
cd test
echo "this is file1" > app.log      # create/overwrite
echo "this is file2" >> app.log     # ⭐ APPEND
cat app.log
```
> 💡 The pair `data.sh` vs `script1.sh` exists purely to burn in the `>` vs `>>` difference.
> **`>` destroys, `>>` adds.** Getting this wrong on a log file loses data.
>
> ⚠️ Also note: these scripts `mkdir` without `-p`, so re-running them fails with
> "File exists". Real scripts use `mkdir -p data1`.

### 4. `variable.sh` — variables and the wrong way
```bash
#!/bin/bash

variable="Hello, World!"
echo $variable

#ls="myfile" -- wrong way
#we can't use commands names as a variable name

name="Nensi"
roll_no=123
comment="Awesome"
echo "My name is $name"
echo "My roll number is $roll_no"
echo "I am $comment"
```

### 5. `input.sh` — interactive input
```bash
#!/bin/bash

read -p "Enter your name: " name
read -p "Enter your roll number: " roll_no
read -p "Enter your comment: " comment

echo  "My name is $name"
echo "My roll number is $roll_no"
echo "My comment is: $comment"
```

### 6. `condition.sh` — age classifier
See [Conditions](#-conditions).

### 7. `loop.sh` / `while_loop1.sh` / `while_loop.sh`
See [Loops](#-loops).

### 8. `function.sh` — function definition (with the calling bug fixed)
See [Functions](#-functions).

### 9. `test1.sh` — the combined "system report" script
```bash
#!/bin/bash

mkdir result_file
cd result_file
touch result.log
echo "This is my result file" > result.log
date
echo hostname
echo whoami
df -h
ps > process.log

read -p "Enter your name: " name
read -p "Enter your roll number: " roll_no

current_date=$(date)
echo "My name is $name" >> result.log
```

This script pulls together everything from the session: directory creation, file creation,
redirection (`>` and `>>`), system commands (`date`, `df -h`, `ps`), capturing output to a file,
reading input, and command substitution.

**Two bugs to learn from:**
```bash
echo hostname      # ❌ prints the literal word "hostname"
echo whoami        # ❌ prints the literal word "whoami"
# ✅ correct:
echo "$(hostname)"
echo "$(whoami)"
# or simply:
hostname
whoami
```

### 10. `task.md` — the session's checklist and its script

The task list was:
```
# print current date              → date
# hostname and username           → hostname whoami who w
# process ps
# add process info inside a file named process.log  →  > process.log
# print name, roll_no, comment
# use variables, take input, create file and directory
```

**A corrected, hardened version of that script:**
```bash
#!/usr/bin/env bash
set -euo pipefail

# --- current date ---
current_date=$(date)
echo "Date        : $current_date"

# --- hostname and username ---
echo "Hostname    : $(hostname)"
echo "Username    : $(whoami)"
echo "Logged in   : $(who | wc -l) user(s)"

# --- processes into a file ---
ps aux > process.log
echo "Saved $(wc -l < process.log) process lines to process.log"

# --- user details ---
read -rp "Enter your name: " name
read -rp "Enter your roll number: " roll_no
read -rp "Enter your comment: " comment

echo "My name is $name"
echo "My roll number is $roll_no"
echo "My comment is: $comment"

# --- create a directory and a report file ---
mkdir -p result_file                       # ⭐ -p = no error if it already exists
report="result_file/result_$(date +%Y%m%d_%H%M%S).log"
{
  echo "Report generated : $current_date"
  echo "Host             : $(hostname)"
  echo "User             : $(whoami)"
  echo "Name             : $name"
  echo "Roll no          : $roll_no"
  echo "Comment          : $comment"
  echo "--- Disk usage ---"
  df -h
} > "$report"

echo "Report written to $report"
```

---

## 🛠️ Practical Automation Scripts

### 1. Disk-space alert (classic cron job)
```bash
#!/usr/bin/env bash
set -euo pipefail

THRESHOLD=80
usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if (( usage > THRESHOLD )); then
  echo "WARNING: root filesystem is ${usage}% full (threshold ${THRESHOLD}%)"
  du -sh /var/log/* 2>/dev/null | sort -h | tail -5
  exit 1
fi
echo "OK: disk usage ${usage}%"
```
```
# crontab: check every 30 minutes
*/30 * * * * /opt/scripts/disk_alert.sh >> /var/log/disk_alert.log 2>&1
```

### 2. Service watchdog
```bash
#!/usr/bin/env bash
set -uo pipefail

for svc in nginx docker sshd; do
  if systemctl is-active --quiet "$svc"; then
    echo "✅ $svc is running"
  else
    echo "❌ $svc is DOWN — restarting"
    systemctl restart "$svc" && echo "   restarted $svc"
  fi
done
```

### 3. Log cleanup / rotation helper
```bash
#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="/var/log/myapp"
DAYS=7

echo "Compressing logs older than 1 day..."
find "$LOG_DIR" -name "*.log" -type f -mtime +1 -exec gzip {} \;

echo "Deleting archives older than ${DAYS} days..."
find "$LOG_DIR" -name "*.gz" -type f -mtime +"$DAYS" -delete

echo "Remaining size: $(du -sh "$LOG_DIR" | cut -f1)"
```

### 4. Timestamped backup
```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="${1:?Usage: $0 <source-dir>}"
DEST="/backup"
STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="${DEST}/$(basename "$SRC")_${STAMP}.tar.gz"

mkdir -p "$DEST"
tar -czf "$ARCHIVE" -C "$(dirname "$SRC")" "$(basename "$SRC")"
echo "Created $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

# keep only the 5 newest backups
ls -1t "${DEST}"/*.tar.gz | tail -n +6 | xargs -r rm -f
```

### 5. HTTP health check with retries
```bash
#!/usr/bin/env bash
set -uo pipefail

URL="${1:-http://localhost:8080/health}"
RETRIES=5

for i in $(seq 1 "$RETRIES"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$URL" || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "✅ $URL healthy (HTTP $code) on attempt $i"
    exit 0
  fi
  echo "Attempt $i/$RETRIES → HTTP $code"
  sleep 3
done

echo "❌ $URL unhealthy after $RETRIES attempts" >&2
exit 1
```

### 6. Container entrypoint that waits for its DB
```bash
#!/bin/sh
# entrypoint.sh — note #!/bin/sh because Alpine has no bash
set -eu

: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:=3306}"

echo "Waiting for ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 2
done
echo "Database is up — starting application"

exec "$@"        # ⭐ exec replaces the shell with the app → app becomes PID 1
                 #    so it receives SIGTERM from `docker stop` directly
```

---

## ✅ Best Practices

| # | Practice | Why |
|---|---|---|
| 1 | Start with `#!/usr/bin/env bash` | Portable interpreter selection |
| 2 | ⭐ `set -euo pipefail` | Fail fast instead of continuing broken |
| 3 | ⭐ **Always quote** `"$var"` | Prevents word-splitting/glob bugs |
| 4 | Use `${VAR}` braces | Unambiguous, safe concatenation |
| 5 | `local` inside functions | Avoids accidental global mutation |
| 6 | Absolute paths in cron/systemd | Their `$PATH` is minimal |
| 7 | Validate inputs early (`$#`, `-f`, `:?`) | Clear errors instead of weird failures |
| 8 | Log with timestamps to stdout/stderr | Errors → `>&2` so pipes stay clean |
| 9 | `mkdir -p`, `rm -f` for idempotency | Re-running the script must be safe |
| 10 | `trap ... EXIT` for cleanup | No orphaned temp files/locks |
| 11 | Never hard-code secrets | Use env vars / a secret manager; `chmod 600` any file that holds them |
| 12 | Run `shellcheck` + `bash -n` | Catches most bugs before runtime |
| 13 | Add a usage/help message | Future-you will need it |
| 14 | Keep scripts small & focused | Past ~150 lines, consider Python |
| 15 | Version-control your scripts | They are infrastructure |

---

## 📋 Quick Cheat Sheet

```bash
# ---------- STRUCTURE ----------
#!/usr/bin/env bash
set -euo pipefail
chmod +x script.sh && ./script.sh

# ---------- VARIABLES ----------
name="value"                 # no spaces around =
echo "${name}"               # quote + brace
export VAR="x"               # visible to child processes
readonly PI=3.14
"${VAR:-default}"            # default if unset
"${VAR:?required}"           # abort if unset

# ---------- INPUT / ARGS ----------
read -rp "Prompt: " var
read -rsp "Password: " pass
$1 $2 ... $# $@ $0 $?

# ---------- SUBSTITUTION ----------
now=$(date +%Y%m%d_%H%M%S)
sum=$(( a + b ))

# ---------- CONDITIONS ----------
if [ "$a" -eq "$b" ]; then ... elif ... else ... fi
[ -f file ] [ -d dir ] [ -z "$s" ] [ -n "$s" ]
-eq -ne -lt -le -gt -ge          # numbers
=  != -z -n                      # strings
[[ $s == pat* ]]  [[ $s =~ ^re$ ]]  (( n > 5 ))
case "$1" in start) ;; *) ;; esac

# ---------- LOOPS ----------
for i in {1..5}; do ... done
for ((i=0;i<5;i++)); do ... done
for f in *.log; do ... done
while [ $n -lt 5 ]; do ((n++)); done
while true; do ... break ... continue ... done
until curl -sf "$URL"; do sleep 2; done
while IFS= read -r line; do ...; done < file

# ---------- FUNCTIONS ----------
myfunc() { local a="$1"; echo "$a"; }
myfunc "arg"                 # call WITHOUT parentheses

# ---------- REDIRECTION ----------
cmd > file      # overwrite        cmd >> file    # append
cmd 2> err      # stderr           cmd > f 2>&1   # both
cmd < in        # stdin            cmd &>/dev/null# discard all
cmd1 | cmd2     # pipe             cmd | tee f    # screen + file
cmd1 && cmd2    # if success       cmd1 || cmd2   # if failure
find . -name "*.tmp" | xargs rm -f

# ---------- DEBUG ----------
bash -n script.sh    # syntax check
bash -x script.sh    # trace
shellcheck script.sh # lint
dos2unix script.sh   # fix CRLF
```

---

## 🔗 References
- Bash manual — https://www.gnu.org/software/bash/manual/
- ShellCheck — https://www.shellcheck.net/
- Google Shell Style Guide — https://google.github.io/styleguide/shellguide.html
- Course repo — https://github.com/Nency-Ravaliya/devops-heros
