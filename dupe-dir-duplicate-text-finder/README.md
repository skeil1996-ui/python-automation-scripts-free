# Dupe Dir Lite – Duplicate Text Finder (free)

Finds near-duplicate text files in a single folder. Standard library only, Python 3.8+.

## Usage

```
python tool.py /path/to/folder
python tool.py /path/to/folder --threshold 0.9 --min-chars 30
```

## Lite limitations

- One folder only (subfolders are not scanned)
- TXT and MD files only (no CSV)
- Console output only (no reports, no JSON)
- Read-only: files are never moved or deleted

## Full version

Recursive scanning, CSV support, reports, exclude patterns and quarantine:
https://skeilster.gumroad.com/l/jjulwj

## Tests

```
python -m unittest test_tool.py
```
