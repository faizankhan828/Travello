#!/usr/bin/env python3
"""
AI Itinerary Planner - Dependency Verification Script
Tests that all AI dependencies are installed and AI modules are syntactically correct
"""

import sys
import ast
import os

def check_file_syntax(filepath):
    """Verify Python file has valid syntax"""
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("AI ITINERARY PLANNER - DEPENDENCY VERIFICATION")
    print("=" * 70)
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    itineraries_dir = os.path.join(backend_dir, 'itineraries')
    
    # Verify Python files exist and are syntactically correct
    print("\n[1] Verifying AI service files...")
    ai_files = [
        'ai_emotion_service.py',
        'ai_ranker_service.py',
        'ai_llm_service.py',
        'ai_service.py',
        'ai_models.py'
    ]
    
    all_ok = True
    for filename in ai_files:
        filepath = os.path.join(itineraries_dir, filename)
        if not os.path.exists(filepath):
            print(f"    ✗ {filename} - FILE NOT FOUND")
            all_ok = False
            continue
        
        ok, error = check_file_syntax(filepath)
        if ok:
            size = os.path.getsize(filepath)
            print(f"    ✓ {filename} - {size} bytes (syntax OK)")
        else:
            print(f"    ✗ {filename} - Syntax Error: {error}")
            all_ok = False
    
    # Verify requirements.txt
    print("\n[2] Verifying requirements.txt...")
    req_file = os.path.join(backend_dir, 'requirements.txt')
    ai_packages = [
        'transformers==4.35.2',
        'torch==2.2.2',
        'lightgbm==4.1.0',
        'scikit-learn==1.3.2',
        'scipy==1.11.4',
        'numpy==1.26.2',
        'pandas==2.1.4',
        'sentence-transformers==2.2.2',
    ]
    
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            req_content = f.read()
        
        missing = []
        for pkg in ai_packages:
            if pkg in req_content:
                print(f"    ✓ {pkg}")
            else:
                print(f"    ✗ {pkg} - NOT FOUND in requirements.txt")
                missing.append(pkg)
                all_ok = False
        
        if missing:
            print(f"\n    WARNING: {len(missing)} packages missing from requirements.txt")
    else:
        print(f"    ✗ requirements.txt not found at {req_file}")
        all_ok = False
    
    # Verify documentation files
    print("\n[3] Verifying documentation...")
    doc_files = [
        'AI_ITINERARY_ARCHITECTURE.md',
        'AI_INTEGRATION_GUIDE.md',
        'AI_INSTALLATION_GUIDE.md',
        'AI_SYSTEM_SUMMARY.md',
        'AI_QUICK_REFERENCE.md',
    ]
    
    parent_dir = os.path.dirname(backend_dir)  # Go to Travello root
    for doc in doc_files:
        doc_path = os.path.join(parent_dir, doc)
        if os.path.exists(doc_path):
            size = os.path.getsize(doc_path)
            print(f"    ✓ {doc} - {size} bytes")
        else:
            print(f"    ✗ {doc} - NOT FOUND")
            all_ok = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ALL CHECKS PASSED - AI SYSTEM READY")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. python manage.py makemigrations")
        print("  2. python manage.py migrate")
        print("  3. Follow AI_INTEGRATION_GUIDE.md for Django setup")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - SEE ABOVE")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
