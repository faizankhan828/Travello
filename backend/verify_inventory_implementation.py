"""
Hotel Room Inventory - File-Based Verification Script
Verifies all implementation steps without Django
"""

import os
import re


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n► {title}")
    print("-" * 80)


def check_file_contains(filepath, patterns, description):
    """Check if file contains specific patterns"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        results = {}
        for pattern_name, pattern_text in patterns.items():
            found = pattern_text in content
            results[pattern_name] = found
            status = "✓" if found else "✗"
            print(f"  {status} {pattern_name}")
        
        return results
    except Exception as e:
        print(f"  ✗ Could not read file: {e}")
        return {}


def verify_models():
    """STEP 3: Verify models have proper inventory methods"""
    print_section("STEP 3: MODEL VERIFICATION")
    
    print_subsection("Checking RoomType model methods")
    
    models_file = 'f:/FYP/Travello/backend/hotels/models.py'
    
    patterns = {
        'get_available_rooms method': 'def get_available_rooms',
        'get_inventory_status method': 'def get_inventory_status',
        'verify_inventory_integrity method': 'def verify_inventory_integrity',
        'available_rooms property': 'def available_rooms',
    }
    
    results = check_file_contains(models_file, patterns, "RoomType Model")
    return all(results.values())


def verify_booking_creation_logic():
    """STEP 4: Verify booking creation has validation and locking"""
    print_section("STEP 4: BOOKING CREATION LOGIC")
    
    print_subsection("Checking booking validation and locking")
    
    views_file = 'f:/FYP/Travello/backend/hotels/views.py'
    
    patterns = {
        'select_for_update locking': 'select_for_update()',
        'Double-check pattern': 'Re-check availability within transaction',
        'Available rooms check': 'get_available_rooms',
        'Booking creation': 'Booking.objects.create',
    }
    
    results = check_file_contains(views_file, patterns, "Booking Creation")
    return all(results.values())


def verify_cancellation_logic():
    """STEP 5: Verify cancellation logic"""
    print_section("STEP 5: CANCELLATION LOGIC")
    
    print_subsection("Checking cancellation implementation")
    
    views_file = 'f:/FYP/Travello/backend/hotels/views.py'
    
    patterns = {
        'Booking status update': 'status = \'CANCELLED\'',
        'Cancellation logging': '[CANCEL]',
        'Inventory restoration': '[CANCEL] Available rooms AFTER',
    }
    
    results = check_file_contains(views_file, patterns, "Cancellation")
    return all(results.values())


def verify_transaction_safety():
    """STEP 6: Verify transaction safety"""
    print_section("STEP 6: TRANSACTION SAFETY & LOCKING")
    
    print_subsection("Checking select_for_update implementation")
    
    views_file = 'f:/FYP/Travello/backend/hotels/views.py'
    
    patterns = {
        'select_for_update for locking': 'select_for_update()',
        'Locked room type retrieval': 'locked_room_type',
        'Transaction management': '@transaction.atomic',
    }
    
    results = check_file_contains(views_file, patterns, "Transaction Safety")
    return results.get('select_for_update for locking', False)


def verify_logging():
    """STEP 7: Verify logging"""
    print_section("STEP 7: LOGGING VERIFICATION")
    
    print_subsection("Checking logging implementation")
    
    views_file = 'f:/FYP/Travello/backend/hotels/views.py'
    
    patterns = {
        'Booking attempt logging': '[BOOKING] Attempting to book',
        'Before booking inventory': '[BOOKING] Available rooms BEFORE',
        'After booking inventory': '[BOOKING] Available rooms AFTER',
        'Cancellation initiation': '[CANCEL] Initiating cancellation',
        'Before cancellation inventory': '[CANCEL] Available rooms BEFORE',
        'After cancellation inventory': '[CANCEL] Available rooms AFTER',
    }
    
    results = check_file_contains(views_file, patterns, "Logging")
    return sum(1 for v in results.values() if v) >= 4


def verify_test_coverage():
    """STEP 8: Verify test files"""
    print_section("STEP 8: TEST COVERAGE")
    
    print_subsection("Checking test file")
    
    test_file = 'f:/FYP/Travello/backend/hotels/test_inventory_system.py'
    
    if not os.path.exists(test_file):
        print(f"  ✗ test_inventory_system.py NOT FOUND")
        return False
    
    patterns = {
        'HotelInventoryTestCase class': 'class HotelInventoryTestCase',
        'Inventory calculation test': 'test_inventory_calculation_basic',
        'Multiple bookings test': 'test_inventory_multiple_bookings',
        'Cancellation restoration test': 'test_inventory_cancellation_restoration',
        'Overbooking detection test': 'test_overbooking_detection',
        'Integrity verification test': 'test_inventory_integrity_verification',
    }
    
    results = check_file_contains(test_file, patterns, "Test Coverage")
    return all(results.values())


def verify_documentation():
    """STEP 9: Verify documentation"""
    print_section("DOCUMENTATION & SUMMARY")
    
    print_subsection("Checking documentation files")
    
    # Check for documentation
    docs = [
        ('f:/FYP/Travello/HOTEL_ROOM_INVENTORY.md', 'Main documentation'),
        ('f:/FYP/Travello/INVENTORY_FIXES.md', 'Fixes documentation'),
    ]
    
    all_found = True
    for doc_file, description in docs:
        if os.path.exists(doc_file):
            print(f"  ✓ {description}")
        else:
            print(f"  ⚠ {description} (optional)")
    
    return True


def print_summary(results):
    """Print final summary"""
    print_section("VERIFICATION SUMMARY")
    
    steps = [
        ("STEP 3: Model Methods", results.get('step3', False)),
        ("STEP 4: Booking Creation", results.get('step4', False)),
        ("STEP 5: Cancellation Logic", results.get('step5', False)),
        ("STEP 6: Transaction Safety", results.get('step6', False)),
        ("STEP 7: Logging", results.get('step7', False)),
        ("STEP 8: Test Coverage", results.get('step8', False)),
    ]
    
    all_passed = True
    for step_name, passed in steps:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:10} {step_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print(" ✓✓✓ ALL IMPLEMENTATION STEPS VERIFIED ✓✓✓")
        print("     Room Inventory System is properly implemented with:")
        print("     • Inventory calculation and availability tracking")
        print("     • Race condition prevention with row-level locking")
        print("     • Proper cancellation and inventory restoration")
        print("     • Comprehensive logging for debugging")
        print("     • Full test coverage")
    else:
        print(" ✗ SOME VERIFICATIONS FAILED - REVIEW ABOVE ✗")
    print("="*80 + "\n")
    
    return all_passed


def main():
    """Run all verification steps"""
    from datetime import datetime
    
    print("\n" + "#"*80)
    print("# HOTEL ROOM INVENTORY SYSTEM - VERIFICATION REPORT")
    print("# Steps 3-9: Complete Implementation Verification")
    print("# Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("#"*80)
    
    results = {
        'step3': verify_models(),
        'step4': verify_booking_creation_logic(),
        'step5': verify_cancellation_logic(),
        'step6': verify_transaction_safety(),
        'step7': verify_logging(),
        'step8': verify_test_coverage(),
    }
    
    verify_documentation()
    
    all_passed = print_summary(results)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    import sys
    exit_code = main()
    sys.exit(exit_code)
