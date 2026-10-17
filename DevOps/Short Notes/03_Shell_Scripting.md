# ⚡ S03 · Shell Scripting

> *Revision card.* Full notes → [Session 3](../03_Shell_Scripting.md)

---

## 🔑 One-line core

***`set -euo pipefail` + always quote `"$var"`.*** Everything else is syntax.

---

## 🧱 The skeleton

```bash
#!/usr/bin/env bash
set -euo pipefail      # ⭐ exit on error · unset var · pipeline failure
IFS=$'\n\t'
trap 'echo "failed at line $LINENO"' ERR
```

| Flag | Stops you from |
|---|---|
| `-e` | sailing past a failed command |
| `-u` | using a typo'd variable as empty |
| `-o pipefail` | ignoring a failure mid-pipe |

---

## 📦 Variables — the three bugs

```bash
NAME="value"      # ✅
NAME = "value"    # ❌ runs a command called NAME
echo "$NAME"      # ✅ safe with spaces / empty
echo $NAME        # ❌ word-splits
```

| Form | Means |
|---|---|
| `${v:-def}` | default if unset |
| `${v:?msg}` | **fail** if unset |
| `${#v}` | length |
| `$(cmd)` | command substitution (not backticks) |

---

## 🎛️ Arguments

| | |
|---|---|
| `$0` | script name |
| `$1 $2` | positional |
| `$@` | all, **individually** (quote it: `"$@"`) |
| `$#` | count |
| `$?` | **last exit code** |
| `$$` | PID |

---

## 🔀 Conditions

```bash
[[ -f file ]]     # exists & regular
[[ -d dir  ]]     # directory
[[ -z "$s" ]]     # empty      [[ -n "$s" ]]  non-empty
[[ $a -eq $b ]]   # numbers: -eq -ne -lt -gt -le -ge
[[ "$a" == "$b" ]]  # strings: ==  !=  =~
```

> ⭐ Prefer `[[ ]]` over `[ ]` — safer, supports `&&`, `=~`.

---

## 🧩 Functions

```bash
greet() {
    local name="$1"        # ⭐ local, or it's global
    echo "hi $name"
}

greet "world"              # ✅ call WITHOUT parentheses
greet()                    # ❌ that's a definition
```

---

## 🚰 Redirection — one character, big difference

| | |
|---|---|
| `>` | **overwrite** |
| `>>` | **append** |
| `2>` | stderr |
| `&>` / `2>&1` | both |
| `< file` | stdin |
| `\| ` | pipe stdout → stdin |
| `/dev/null` | discard |
| `<<EOF … EOF` | here-doc |

---

## 🔢 Exit codes

| | |
|---|---|
| **0** | success |
| 1 | general error |
| **127** | command not found |
| 126 | not executable |
| **137** | SIGKILL / OOM |
| **143** | SIGTERM |

---

## ⚠️ Traps

- Unquoted `$var` — *the* most common shell bug
- `name()` instead of `name` when calling
- Forgetting `local` → silent global clobber
- `>` where you meant `>>`
- CRLF line endings

---

## 🧰 Before you run it

```bash
shellcheck script.sh      # ⭐ lints every bug above
bash -x script.sh         # trace each expanded line
```

---

## 🎤 Rapid fire

| Q | A |
|---|---|
| First line of every script? | `set -euo pipefail` |
| `$@` vs `$*`? | separate words vs one string |
| Capture output? | `out=$(cmd)` |
| Script works, exit code 0, but a step failed? | missing `-e` / `pipefail` |

---

⬅️ [S02](./02_Linux_Fundamentals.md) · ➡️ [S04 · Networking](./04_Networking_Fundamentals.md)
