---
name: quick-script
description: Write or run a small, throwaway Python script with no imposed project structure or test requirement. Use for one-off automation, exploration, or a short utility that isn't meant to be maintained long-term.
when_to_use: Use when the user asks for a quick script, a one-off data check, or a small automation and does not mention packaging, distribution, or long-term maintenance.
---

# Quick script

For a single-file or small throwaway Python script:

1. Write it as a plain `.py` file (or a short `if __name__ == "__main__":`
   script) — no package layout, no `pyproject.toml`, no test suite required.
2. Still follow the Python style rule's basics (formatting, no bare
   `except:`), since that costs nothing extra.
3. Add a one-line docstring or comment at the top only if the script's
   purpose isn't obvious from its name and arguments.
4. If the script grows real users, gets scheduled, or needs distribution,
   switch to `ship-tool` instead of continuing to bolt features onto a
   throwaway script.
