# !/usr/bin/env python3.
"""Bulk comment shortener for the RagView project.

The script walks the repository, finds comment lines in supported languages,
and rewrites each comment to a concise, single‑sentence version while preserving
indentation and the comment marker.

Supported comment prefixes:
  • Python:      #
  • JavaScript/TypeScript: //, /*
  • HTML/CSS:   <!-- … -->   (treated as a single‑line comment for simplicity)

Usage (from the project root):
    python scripts/bulk_comment_edit.py

The script is safe to run multiple times – it only trims overly long comments
and will not alter code.
"""
import pathlib
import re
import sys

# ----------------------------------------------------------------------.
# Configuration.
# ----------------------------------------------------------------------.
PROJECT_ROOT = pathlib.Path("d:/RAG view")
MAX_LEN = 80                      # max characters for a comment without a period
VERBOSE = True                    # print each modified file

def shorten(text: str) -> str:
    """Return a shortened version of a comment string.
    Keeps characters up to the first period; if none, truncates to MAX_LEN.
    """
    sentence = text.split('.', 1)[0].strip()
    if sentence:
        return sentence + '.'
    return text[:MAX_LEN].strip()

def process_file(path: pathlib.Path) -> bool:
    """Rewrite the file in‑place; return True if it was modified."""
    original = path.read_text(encoding='utf-8')
    lines = original.splitlines(keepends=True)
    changed = False
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # Python comment.
        if stripped.startswith('#'):
            prefix = line[:len(line) - len(stripped)]
            comment_body = stripped[1:].strip()
            if comment_body:
                short = shorten(comment_body)
                new_line = f"{prefix}# {short}\n"
                if new_line != line:
                    changed = True
                    line = new_line
        # JS/TS single‑line comment.
        elif stripped.startswith('//'):
            prefix = line[:len(line) - len(stripped)]
            comment_body = stripped[2:].strip()
            if comment_body:
                short = shorten(comment_body)
                new_line = f"{prefix}// {short}\n"
                if new_line != line:
                    changed = True
                    line = new_line
        # Block comment start.
        elif stripped.startswith('/*'):
            # Find end of block on same line.
            end_idx = line.find('*/')
            if end_idx != -1:
                prefix = line[:len(line) - len(stripped)]
                comment_body = stripped[2:end_idx].strip()
                if comment_body:
                    short = shorten(comment_body)
                    new_line = f"{prefix}/* {short} */\n"
                    if new_line != line:
                        changed = True
                        line = new_line
            else:
                # Multi‑line block – replace first line, skip until closing */.
                prefix = line[:len(line) - len(stripped)]
                comment_body = stripped[2:].strip()
                short = shorten(comment_body)
                new_line = f"{prefix}/* {short} */\n"
                changed = True
                line = new_line
                # Skip following lines until we encounter */.
                i += 1
                while i < len(lines) and '*/' not in lines[i]:
                    i += 1
                # Skip the closing line as well.
        # HTML/CSS comment.
        elif stripped.startswith('<!--'):
            prefix = line[:len(line) - len(stripped)]
            comment_body = stripped[4:].split('-->', 1)[0].strip()
            short = shorten(comment_body)
            new_line = f"{prefix}<!-- {short} -->\n"
            if new_line != line:
                changed = True
                line = new_line
        new_lines.append(line)
        i += 1
    if changed:
        path.write_text(''.join(new_lines), encoding='utf-8')
        if VERBOSE:
            print(f"Updated comments in {path}")
    return changed

def main():
    patterns = ['*.py', '*.js', '*.ts', '*.tsx', '*.jsx', '*.html', '*.css']
    any_change = False
    for pattern in patterns:
        for file_path in PROJECT_ROOT.rglob(pattern):
            try:
                if process_file(file_path):
                    any_change = True
            except Exception as exc:
                print(f'⚠️  Failed on {file_path}: {exc}', file=sys.stderr)
    if not any_change:
        print('No comment changes were necessary – all comments already short.')

if __name__ == '__main__':
    main()

