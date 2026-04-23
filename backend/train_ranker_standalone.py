"""
Standalone training script for the itinerary ranker model.
Doesn't rely on Django, pure Python.
"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend')

# Setup Django
import os
import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

from itineraries.ranker_model_trainer import RankerModelTrainer

if __name__ == '__main__':
    print("=" * 60)
    print("ITINERARY RANKER MODEL TRAINING")
    print("=" * 60)
    
    trainer = RankerModelTrainer(verbose=True)
    
    result = trainer.full_train_pipeline(
        city='Lahore',
        output_path='ml_models/itinerary_ranker.pkl',
        use_synthetic=True
    )
    
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Model saved to: {result['model_path']}")
    print(f"\nMetrics:")
    print(f"  Train RMSE: {result['metrics']['train_rmse']:.4f}")
    print(f"  Test RMSE:  {result['metrics']['test_rmse']:.4f}")
    print(f"  Train MAE:  {result['metrics']['train_mae']:.4f}")
    print(f"  Test MAE:   {result['metrics']['test_mae']:.4f}")
    print(f"  Train R²:   {result['metrics']['train_r2']:.4f}")
    print(f"  Test R²:    {result['metrics']['test_r2']:.4f}")
    print(f"\nData Summary:")
    print(f"  Total samples: {result['data_summary']['total_training_samples']}")
    print(f"  Positive: {result['data_summary']['positive_samples']}")
    print(f"  Negative: {result['data_summary']['negative_samples']}")
