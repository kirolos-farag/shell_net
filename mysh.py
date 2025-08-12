#!/usr/bin/env python3
"""
mysh.py - A Python-based interactive shell (Unix-like features)
Features:
 - Builtin commands: ls, cd, pwd, cat, head, tail, grep, cp, mv, rm, mkdir, rmdir, touch, find, info, history, clear, exit
 - Tab completion for commands and filesystem
 - Command history (persisted to ~/.mysh_history)
 - Piping '|' and redirection '>' '>>'
 - Fallback to external commands when not builtin
Dependencies: prompt_toolkit
Install: pip install prompt_toolkit
"""

import os
import sys
import shlex
import shutil
import fnmatch
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Any
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
    from prompt_toolkit.history import FileHistory
except Exception:
    print("Missing prompt_toolkit. Install with: pip install prompt_toolkit")
    sys.exit(1)

HISTORY_FILE = Path.home() / ".mysh_history"
SHELL_NAME = "mysh"

# -----------------------
# Utilities
# -----------------------
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def read_file_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_to_file_text(path, text, append=False):
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8", errors="replace") as f:
        f.write(text)
# -----------------------
# Builtin command implementations
# -----------------------
def builtin_pwd(args, stdin=None):
    print(os.getcwd())

def builtin_cd(args, stdin=None):
    if len(args) == 0:
        target = str(Path.home())
    else:
        target = args[0]
    try:
        os.chdir(os.path.expanduser(target))
    except Exception as e:
        eprint("cd:", e)

def builtin_ls(args, stdin=None):
    path = args[0] if args else "."
    try:
        entries = sorted(os.listdir(path))
        for name in entries:
            p = Path(path) / name
            if p.is_dir():
                print(name + "/")
            elif os.access(p, os.X_OK):
                print(name)
            else:
                print(name)
    except Exception as e:
        eprint("ls:", e)

def builtin_cat(args, stdin=None):
    if not args and stdin is not None:
        print(stdin, end="")
        return
    for fname in args:
        try:
            print(read_file_text(fname), end="")
        except Exception as e:
            eprint("cat:", e)

def builtin_head(args, stdin=None):
    n = 10
    files = []
    if args and args[0].startswith("-"):
        try:
            n = int(args[0].lstrip("-n"))
            files = args[1:]
        except:
            files = args[1:]
    else:
        files = args
    if not files and stdin is not None:
        lines = stdin.splitlines(True)[:n]
        print(''.join(lines), end="")
        return
    for fname in files:
        try:
            with open(fname, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i >= n: break
                    print(line, end="")
        except Exception as e:
            eprint("head:", e)

def builtin_tail(args, stdin=None):
    n = 10
    files = []
    if args and args[0].startswith("-"):
        try:
            n = int(args[0].lstrip("-n"))
            files = args[1:]
        except:
            files = args[1:]
    else:
        files = args
    if not files and stdin is not None:
        lines = stdin.splitlines(True)[-n:]
        print(''.join(lines), end="")
        return
    for fname in files:
        try:
            with open(fname, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-n:]
                print(''.join(lines), end="")
        except Exception as e:
            eprint("tail:", e)

def builtin_grep(args, stdin=None):
    if not args:
        eprint("grep: missing pattern")
        return
    pattern = args[0]
    files = args[1:] if len(args) > 1 else []
    if not files and stdin is not None:
        for line in stdin.splitlines():
            if pattern in line:
                print(line)
        return
    for fname in files:
        try:
            with open(fname, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if pattern in line:
                        print(f"{fname}:{line}", end="")
        except Exception as e:
            eprint("grep:", e)

def builtin_cp(args, stdin=None):
    if len(args) < 2:
        eprint("cp: missing arguments")
        return
    srcs, dst = args[:-1], args[-1]
    try:
        if len(srcs) > 1 or os.path.isdir(srcs[0]):
            # copy multiple into directory
            for s in srcs:
                shutil.copy(s, dst)
        else:
            shutil.copy(srcs[0], dst)
    except Exception as e:
        eprint("cp:", e)

def builtin_mv(args, stdin=None):
    if len(args) < 2:
        eprint("mv: missing arguments")
        return
    try:
        shutil.move(args[0], args[1])
    except Exception as e:
        eprint("mv:", e)

def builtin_rm(args, stdin=None):
    if not args:
        eprint("rm: missing args")
        return
    for p in args:
        pth = Path(p)
        try:
            if pth.is_dir():
                shutil.rmtree(pth)
            else:
                pth.unlink()
        except Exception as e:
            eprint("rm:", e)

def builtin_mkdir(args, stdin=None):
    if not args:
        eprint("mkdir: missing args")
        return
    for d in args:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            eprint("mkdir:", e)

def builtin_rmdir(args, stdin=None):
    if not args:
        eprint("rmdir: missing args")
        return
    for d in args:
        try:
            os.rmdir(d)
        except Exception as e:
            eprint("rmdir:", e)

def builtin_touch(args, stdin=None):
    if not args:
        eprint("touch: missing args")
        return
    for f in args:
        Path(f).touch(exist_ok=True)

def builtin_find(args, stdin=None):
    start = args[0] if args else "."
    pattern = args[1] if len(args) > 1 else "*"
    for root, dirs, files in os.walk(start):
        for name in files + dirs:
            if fnmatch.fnmatch(name, pattern):
                print(os.path.join(root, name))

def builtin_info(args, stdin=None):
    import platform
    print("OS:", platform.system(), platform.release())
    print("Machine:", platform.machine())
    print("Python:", platform.python_version())
    print("CWD:", os.getcwd())

def builtin_history(args, stdin=None):
    try:
        lines = open(HISTORY_FILE, "r", encoding="utf-8").read().splitlines()
        for i, l in enumerate(lines[-200:], start=1):
            print(f"{i}: {l}")
    except Exception:
        pass

def builtin_clear(args, stdin=None):
    os.system("cls" if os.name == "nt" else "clear")

def builtin_exit(args, stdin=None):
    sys.exit(0)


def builtin_whoami(args, stdin=None):
    """Show current user"""
    if os.name == 'nt':  # Windows
        print(os.getenv('USERNAME', 'Unknown'))
    else:  # Linux/Mac
        print(os.getenv('USER', 'Unknown'))

def builtin_elevate(args, stdin=None):
    """Elevate to admin privileges"""
    if os.name == 'nt':  # Windows
        try:
            # Check if already admin
            if os.getenv('USERNAME') == 'Administrator':
                print("Already running as Administrator")
                return
            
            # Relaunch as admin
            script = os.path.abspath(__file__)
            subprocess.run(['powershell', 'Start-Process', 'python', '-ArgumentList', f'"{script}"', '-Verb', 'RunAs'])
            sys.exit(0)
        except Exception as e:
            eprint(f"Failed to elevate: {e}")
    else:  # Linux/Mac
        try:
            # Check if already root
            if os.geteuid() == 0:
                print("Already running as root")
                return
                
            # Relaunch with sudo
            subprocess.run(['sudo', 'python3', os.path.abspath(__file__)])
            sys.exit(0)
        except Exception as e:
            eprint(f"Failed to elevate: {e}")


BUILTINS = {
    "pwd": builtin_pwd,
    "cd": builtin_cd,
    "ls": builtin_ls,
    "cat": builtin_cat,
    "head": builtin_head,
    "tail": builtin_tail,
    "grep": builtin_grep,
    "cp": builtin_cp,
    "mv": builtin_mv,
    "rm": builtin_rm,
    "mkdir": builtin_mkdir,
    "rmdir": builtin_rmdir,
    "touch": builtin_touch,
    "find": builtin_find,
    "info": builtin_info,
    "history": builtin_history,
    "clear": builtin_clear,
    "exit": builtin_exit,
    "quit": builtin_exit,
    "whoami": builtin_whoami,
    "elevate": builtin_elevate,
    "admin": builtin_elevate,  # alias
    "sudo": builtin_elevate    # alias
}

# -----------------------
# Parser & runner (supports pipes and simple redirection)
# -----------------------
def parse_command_line(line: str) -> List[Tuple[List[str], Optional[str], Optional[str]]]:
    """
    Parse into list of (argv_list, out_path, append_flag)
    Pipes split segments. Each segment may have > or >> redirection at end.
    Returns list in pipeline order.
    """
    parts = [p.strip() for p in line.split("|")]
    pipeline = []
    for part in parts:
        out_path = None
        append = False
        # handle >> first
        if ">>" in part:
            part, rest = part.split(">>", 1)
            out_path = rest.strip().split()[0] if rest.strip() else None
            append = True
        elif ">" in part:
            part, rest = part.split(">", 1)
            out_path = rest.strip().split()[0] if rest.strip() else None
            append = False
        argv = shlex.split(part)
        pipeline.append((argv, out_path, append))
    return pipeline

def run_pipeline(pipeline):
    """
    pipeline: list of (argv, out_path, append_flag)
    We'll execute builtins in-process; if command not builtin, call subprocess.
    Data passing uses text (str).
    """
    data = None  # text passed along pipeline (stdin)
    for i, (argv, out_path, append) in enumerate(pipeline):
        if not argv:
            continue
        cmd = argv[0]
        args = argv[1:]
        # if builtin, call function, capture output to string
        if cmd in BUILTINS:
            # capture print outputs by redirecting stdout temporarily
            from io import StringIO
            old_stdout = sys.stdout
            buf = StringIO()
            sys.stdout = buf
            try:
                BUILTINS[cmd](args, stdin=data)
            except SystemExit:
                sys.stdout = old_stdout
                raise
            except Exception as e:
                sys.stdout = old_stdout
                eprint(f"{cmd}: error: {e}")
                return
            sys.stdout = old_stdout
            out_text = buf.getvalue()
        else:
            # external command fallback
            try:
                proc = subprocess.Popen([cmd] + args,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)
                out_text, err = proc.communicate(input=data, timeout=30)
                if err:
                    # print errors to stderr
                    eprint(err.strip())
            except FileNotFoundError:
                eprint(f"{cmd}: command not found")
                return
            except Exception as e:
                eprint(f"{cmd}: error: {e}")
                return
        # if this stage has redirection, write to file
        if out_path:
            mode = "a" if append else "w"
            try:
                with open(os.path.expanduser(out_path), mode, encoding="utf-8") as f:
                    f.write(out_text)
            except Exception as e:
                eprint("redirection error:", e)
            # after redirection, nothing is passed down unless still piping
            data = ""
        else:
            data = out_text
    # at end of pipeline, print data if any
    if data:
        print(data, end="")

# -----------------------
# Prompt & completion
# -----------------------
class MyCompleter(Completer):
    def __init__(self, commands):
        self.path_completer = PathCompleter(
            expanduser=True,
            only_directories=False,
            file_filter=lambda name: True,
            get_paths=lambda: [os.getcwd()]
        )
        self.cmd_completer = WordCompleter(commands, ignore_case=True)
        self.commands = commands
        
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        
        # Command completion at start or after space
        if not text.strip() or text[-1].isspace():
            for cmd in self.commands:
                if cmd.startswith(word_before_cursor):
                    yield Completion(cmd, start_position=-len(word_before_cursor))
            return
            
        # Path completion for paths
        if any(ch in text for ch in "/\\.~"):
            for c in self.path_completer.get_completions(document, complete_event):
                yield c
        else:
            # Command completion otherwise
            for c in self.cmd_completer.get_completions(document, complete_event):
                yield c

def ensure_history_file():
    try:
        HISTORY_FILE.touch(exist_ok=True)
    except Exception:
        pass

# -----------------------
# Main loop
# -----------------------
def main():
    ensure_history_file()
    commands = list(BUILTINS.keys())
    
    # Initialize session with history
    try:
        session = PromptSession(history=FileHistory(str(HISTORY_FILE)))
    except Exception:
        session = PromptSession()
    
    completer = MyCompleter(commands)
    
    print(f"Welcome to {SHELL_NAME} - Python shell. Type 'help' for builtin commands.")
    
    while True:
        try:
            # Show current directory name in prompt
            cwd = os.getcwd()
            prompt = f"{os.path.basename(cwd)} $ "
            
            line = session.prompt(prompt, completer=completer)
            if not line.strip():
                continue
                
            if line.strip() == "help":
                print("Builtins:", ", ".join(sorted(BUILTINS.keys())))
                print("Supports: pipes | and redirection > >>, tab completion, history (saved).")
                continue
                
            pipeline = parse_command_line(line)
            run_pipeline(pipeline)
            
        except KeyboardInterrupt:
            print("^C")
            continue
        except EOFError:
            print("exit")
            break
        except SystemExit:
            break
        except Exception as e:
            eprint("Shell error:", e)

if __name__ == "__main__":
    main()