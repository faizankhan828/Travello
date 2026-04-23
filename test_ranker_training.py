"""
Quick test script to train the itinerary ranker model.
Run directly: python test_ranker_training.py
"""

import os
import sys
import django

# Add backend to path
sys.path.insert(0, 'backend')
os.chdir('f:\\FYP\\Travello')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')
django.setup()

from itineraries.ranker_model_trainer import RankerModelTrainer

def main():
    print("=" * 60)
    print("Itinerary Ranker Model Training")
    print("=" * 60)
    
    trainer = RankerModelTrainer(verbose=True)
    
    try:
        result = trainer.full_train_pipeline(
            city='Lahore',
            output_path='ml_models/itinerary_ranker.pkl',
            use_synthetic=True
        )
        
        print("\n" + "=" * 60)
        print("TRAINING COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Model saved to: {result['model_path']}")
        print(f"\nMetrics:")
        print(f"  Test RMSE: {result['metrics']['test_rmse']:.4f}")
        print(f"  Test MAE: {result['metrics']['test_mae']:.4f}")
        print(f"  Test R²: {result['metrics']['test_r2']:.4f}")
        print(f"\nData Summary:")
        print(f"  Total Samples: {result['data_summary']['total_training_samples']}")
        print(f"  Positive: {result['data_summary']['positive_samples']}")
        print(f"  Negative: {result['data_summary']['negative_samples']}")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
