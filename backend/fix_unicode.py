#!/usr/bin/env python
"""Fix Unicode characters in management commands"""

import os
import re

files_to_fix = [
    'itineraries/management/commands/analyze_itinerary_ranker_data.py',
    'itineraries/management/commands/train_itinerary_ranker.py',
]

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First, encode/decode to handle the Unicode
    # Replace Unicode characters with ASCII equivalents
    replacements = {
        '⭐': '[STAR]',
        '📊': '[CHART]',
        '🌟': '[STAR]',
        '✓': '[OK]',
        '✗': '[FAIL]',
        '⚠': '[WARN]',
        '─': '-',
        '━': '=',
        '├': '|',
        '└': '|',
        '│': '|',
        '•': '*',
        '—': '-',
        '–': '-',
        'ò': 'o',
        'ù': 'u',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Also handle escape sequences
    content = content.replace('\\u2b50', '[STAR]')  # ⭐
    content = content.replace('\\u2713', '[OK]')     # ✓
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed: {file_path}")

print("Done!")
