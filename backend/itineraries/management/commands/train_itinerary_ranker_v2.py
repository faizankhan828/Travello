"""
Management command to train the itinerary ranker model.

Usage:
    python manage.py train_itinerary_ranker --city Lahore --synthetic
    python manage.py train_itinerary_ranker --verbose
"""

import os
from django.core.management.base import BaseCommand, CommandError
from itineraries.ranker_model_trainer import RankerModelTrainer


class Command(BaseCommand):
    help = 'Train the LightGBM model for itinerary place ranking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            default='Lahore',
            help='City to training on (default: Lahore)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            default='ml_models/itinerary_ranker.pkl',
            help='Path to save trained model'
        )
        
        parser.add_argument(
            '--synthetic',
            action='store_true',
            help='Use synthetic data if real data not available'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        city = options['city']
        output_path = options['output']
        use_synthetic = options['synthetic']
        verbose = options['verbose']
        
        self.stdout.write(f"Starting model training for {city}...")
        
        try:
            trainer = RankerModelTrainer(verbose=verbose)
            result = trainer.full_train_pipeline(
                city=city,
                output_path=output_path,
                use_synthetic=use_synthetic
            )
            
            self.stdout.write(self.style.SUCCESS('[OK] Training complete'))
            self.stdout.write(f"Model saved to: {result['model_path']}")
            self.stdout.write(f"Test RMSE: {result['metrics']['test_rmse']:.4f}")
            self.stdout.write(f"Test MAE: {result['metrics']['test_mae']:.4f}")
            self.stdout.write(f"Test R²: {result['metrics']['test_r2']:.4f}")
            
        except Exception as e:
            raise CommandError(f"Training failed: {str(e)}")
