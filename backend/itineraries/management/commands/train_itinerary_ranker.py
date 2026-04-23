"""
Django Management Command: train_itinerary_ranker

Purpose:
    Train a LightGBM learning-to-rank model for place ranking in itineraries.
    Uses data collected by analyze_itinerary_ranker_data command.

Features:
    1. Collect training data from database
    2. Extract and encode features (no data leakage)
    3. Split into train/test sets
    4. Train LightGBM ranker
    5. Evaluate model performance
    6. Save model to backend/ml_models/
    7. Log metrics and feature importance

Usage:
    python manage.py train_itinerary_ranker
    python manage.py train_itinerary_ranker --verbose
    python manage.py train_itinerary_ranker --city Lahore
    python manage.py train_itinerary_ranker --test-only
"""

import logging
import pickle
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
import os

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)

# Import from the analysis command
from itineraries.management.commands.analyze_itinerary_ranker_data import (
    RankerDataAnalyzer,
    DataSample,
)


class RankerModelTrainer:
    """Train LightGBM model for place ranking"""
    
    # Mapping for categorical variables
    MOOD_TO_ID = {
        'RELAXING': 0, 'SPIRITUAL': 1, 'HISTORICAL': 2, 'FOODIE': 3,
        'FUN': 4, 'SHOPPING': 5, 'NATURE': 6, 'ROMANTIC': 7, 'FAMILY': 8
    }
    
    BUDGET_TO_ID = {'LOW': 0, 'MEDIUM': 1, 'LUXURY': 2}
    
    CATEGORY_TO_ID = {
        'religious': 0, 'history': 1, 'culture': 2, 'food': 3,
        'nature': 4, 'shopping': 5, 'modern': 6, 'other': 7
    }
    
    PACE_TO_ID = {'RELAXED': 0, 'BALANCED': 1, 'PACKED': 2}
    
    # Feature columns in order
    FEATURE_COLUMNS = [
        # User features
        'user_mood_id',
        'user_budget_id',
        'user_pace_id',
        'user_interests_count',
        
        # Place features
        'place_category_id',
        'place_rating',
        'place_budget_id',
        'place_visit_minutes',
        'place_tags_count',
        'place_ideal_start',
        'place_ideal_end',
        
        # Contextual features
        'trip_day',
        'trip_total_days',
        
        # Geographic
        'distance_km',
        
        # Interaction features
        'user_interests_match',  # 1 if place tags in user interests, 0 otherwise
        'budget_match',  # 1 if place budget <= user budget, 0 otherwise
        'cultural_match',  # 1 if cultural place + historical mood, 0 otherwise
    ]
    
    def __init__(self, verbose: bool = False, test_mode: bool = False):
        """Initialize trainer"""
        self.verbose = verbose
        self.test_mode = test_mode
        self.model = None
        self.scaler = None
        self.train_data = None
        self.test_data = None
        self._log("Initialized RankerModelTrainer")
    
    def _log(self, msg: str, level: str = 'info'):
        """Log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {msg}"
        
        if self.verbose:
            print(formatted_msg)
        
        if level == 'error':
            logger.error(msg)
        elif level == 'warning':
            logger.warning(msg)
        else:
            logger.info(msg)
    
    def collect_data(self, city: str = 'Lahore', limit: Optional[int] = None) -> List[DataSample]:
        """
        Collect training data using RankerDataAnalyzer
        
        Args:
            city: City to train on
            limit: Maximum number of itineraries
        
        Returns:
            List of DataSample objects
        """
        self._log(f"Collecting training data for {city}...")
        
        analyzer = RankerDataAnalyzer(verbose=self.verbose)
        report = analyzer.analyze(city=city, limit=limit)
        
        # Log summary
        total_samples = report['data_overview']['total_training_samples']
        positive_samples = report['data_overview']['positive_samples']
        negative_samples = report['data_overview']['negative_samples']
        
        self._log(f"  [OK] Collected {total_samples} training samples")
        self._log(f"    - Positive (selected): {positive_samples}")
        self._log(f"    - Negative (not selected): {negative_samples}")
        
        # Check recommendation
        recommendation = report.get('recommendation', '')
        if 'INSUFFICIENT' in recommendation or 'Not ready' in recommendation:
            self._log(f"  [WARN] Data quality warning: {recommendation}", level='warning')
        
        return analyzer.samples, report
    
    def extract_features(self, samples: List[DataSample]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract and encode features from DataSample objects
        
        VALIDATION: No data leakage - features do NOT include target (was_selected)
        
        Args:
            samples: List of DataSample objects
        
        Returns:
            Tuple of (X, y) where:
            - X: Feature matrix (N, num_features)
            - y: Target vector (N,) - ranking score (0 or 1 from selection_quality)
        """
        self._log("Extracting and encoding features...")
        
        X_list = []
        y_list = []
        
        for sample in samples:
            # -- Feature extraction (NO LEAKAGE) ------------------------------
            # Do NOT include: was_selected, selection_quality in features
            # These are ONLY in the target
            
            # User features
            user_mood_id = self.MOOD_TO_ID.get(sample.user_mood, 0)
            user_budget_id = self.BUDGET_TO_ID.get(sample.user_budget, 0)
            user_pace_id = self.PACE_TO_ID.get(sample.user_pace, 0)
            user_interests_count = len(sample.user_interests) if sample.user_interests else 0
            
            # Place features
            place_category_id = self.CATEGORY_TO_ID.get(sample.place_category.lower(), 7)
            place_rating = sample.place_rating / 5.0  # Normalize to 0-1
            place_budget_id = self.BUDGET_TO_ID.get(sample.place_budget_level, 0)
            place_visit_minutes = sample.place_visit_minutes / 300.0  # Normalize (max typical is 300)
            place_tags_count = len(sample.place_tags) if sample.place_tags else 0
            place_ideal_start = sample.place_ideal_start / 24.0 if sample.place_ideal_start else 0
            place_ideal_end = sample.place_ideal_end / 24.0 if sample.place_ideal_end else 0
            
            # Contextual features
            trip_day = sample.trip_day / sample.trip_total_days if sample.trip_total_days > 0 else 0
            trip_total_days = sample.trip_total_days / 7.0  # Normalize (typical trip ~7 days)
            
            # Geographic
            distance_km = sample.distance_km / 100.0  # Normalize (max typical ~100km)
            
            # Interaction features (derived)
            # Check if any place tags match user interests
            user_interests_match = 1.0 if (
                sample.user_interests and sample.place_tags and
                any(tag.lower() in [i.lower() for i in sample.user_interests]
                    for tag in sample.place_tags)
            ) else 0.0
            
            # Budget match: place budget <= user budget
            budget_match = 1.0 if (
                self.BUDGET_TO_ID.get(sample.place_budget_level, 0) <=
                self.BUDGET_TO_ID.get(sample.user_budget, 0)
            ) else 0.0
            
            # Cultural match: cultural place + appropriate mood
            place_is_cultural = sample.place_category.lower() in ['religious', 'history', 'culture']
            mood_is_cultural = sample.user_mood in ['SPIRITUAL', 'HISTORICAL']
            cultural_match = 1.0 if place_is_cultural and mood_is_cultural else 0.0
            
            # Build feature vector in exact order
            feature_vector = [
                user_mood_id,
                user_budget_id,
                user_pace_id,
                user_interests_count,
                place_category_id,
                place_rating,
                place_budget_id,
                place_visit_minutes,
                place_tags_count,
                place_ideal_start,
                place_ideal_end,
                trip_day,
                trip_total_days,
                distance_km,
                user_interests_match,
                budget_match,
                cultural_match,
            ]
            
            X_list.append(feature_vector)
            
            # -- Target extraction --------------------------------------------
            # Target: Use selection_quality (0-1) as regression target
            # Alternative: Could use binary classification (was_selected)
            y_list.append(sample.selection_quality)
        
        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)
        
        self._log(f"  [OK] Extracted {len(samples)} samples with {X.shape[1]} features")
        self._log(f"    - Feature shape: {X.shape}")
        self._log(f"    - Target shape: {y.shape}")
        self._log(f"    - Target range: [{y.min():.3f}, {y.max():.3f}]")
        
        return X, y
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Train LightGBM model
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_test: Test features
            y_test: Test targets
        
        Returns:
            Dictionary with training metrics
        """
        self._log("Training LightGBM model...")
        
        # Normalize features
        self._log("  Normalizing features...")
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Create LightGBM datasets
        train_data = lgb.Dataset(X_train_scaled, label=y_train)
        test_data = lgb.Dataset(X_test_scaled, label=y_test, reference=train_data)
        
        # LightGBM parameters
        params = {
            'objective': 'regression',  # Regression for ranking scores
            'metric': 'rmse',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
        }
        
        # Train model
        self._log("  Training with LightGBM...")
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=100,
            valid_sets=[train_data, test_data],
            valid_names=['train', 'test'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=10, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        
        # Evaluate
        self._log("  [OK] Model training complete")
        
        # Get predictions
        y_train_pred = self.model.predict(X_train_scaled)
        y_test_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_train_pred)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_test_pred)),
            'train_mae': mean_absolute_error(y_train, y_train_pred),
            'test_mae': mean_absolute_error(y_test, y_test_pred),
            'train_r2': r2_score(y_train, y_train_pred),
            'test_r2': r2_score(y_test, y_test_pred),
            'n_boosting_rounds': self.model.num_trees(),
        }
        
        return metrics
    
    def evaluate(self, metrics: Dict):
        """Log evaluation results"""
        self._log("Model Evaluation Results:")
        self._log(f"  Training RMSE:  {metrics['train_rmse']:.4f}")
        self._log(f"  Test RMSE:      {metrics['test_rmse']:.4f}")
        self._log(f"  Training MAE:   {metrics['train_mae']:.4f}")
        self._log(f"  Test MAE:       {metrics['test_mae']:.4f}")
        self._log(f"  Training R²:    {metrics['train_r2']:.4f}")
        self._log(f"  Test R²:        {metrics['test_r2']:.4f}")
        self._log(f"  Boosting rounds: {metrics['n_boosting_rounds']}")
        
        # Feature importance
        feature_importance = self.model.feature_importance()
        top_features_idx = np.argsort(feature_importance)[-5:][::-1]
        
        self._log("\nTop 5 Important Features:")
        for idx in top_features_idx:
            if idx < len(self.FEATURE_COLUMNS):
                feature_name = self.FEATURE_COLUMNS[idx]
                importance = feature_importance[idx]
                self._log(f"  {idx+1}. {feature_name}: {importance:.0f}")
        
        return metrics
    
    def save_model(self, output_path: str) -> str:
        """
        Save trained model and scaler to disk
        
        Args:
            output_path: Path to save model (e.g., backend/ml_models/itinerary_ranker.pkl)
        
        Returns:
            Full path to saved model
        """
        self._log(f"Saving model to {output_path}...")
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create model package with metadata
        model_package = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.FEATURE_COLUMNS,
            'categorical_mappings': {
                'mood_to_id': self.MOOD_TO_ID,
                'budget_to_id': self.BUDGET_TO_ID,
                'category_to_id': self.CATEGORY_TO_ID,
                'pace_to_id': self.PACE_TO_ID,
            },
            'trained_at': datetime.now().isoformat(),
            'model_type': 'LightGBMRegressor',
            'framework_versions': {
                'lightgbm': lgb.__version__,
                'scikit-learn': '1.0+',
                'numpy': np.__version__,
            }
        }
        
        # Save using pickle
        with open(output_path, 'wb') as f:
            pickle.dump(model_package, f)
        
        self._log(f"  [OK] Model saved to {output_path}")
        
        # Log file size
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        self._log(f"  File size: {file_size_mb:.2f} MB")
        
        return output_path
    
    def load_model(self, model_path: str) -> bool:
        """
        Load trained model from disk
        
        Args:
            model_path: Path to saved model
        
        Returns:
            True if load successful
        """
        try:
            self._log(f"Loading model from {model_path}...")
            
            with open(model_path, 'rb') as f:
                model_package = pickle.load(f)
            
            self.model = model_package['model']
            self.scaler = model_package['scaler']
            
            self._log(f"  [OK] Model loaded successfully")
            return True
        
        except Exception as e:
            self._log(f"  [FAIL] Error loading model: {str(e)}", level='error')
            return False


class Command(BaseCommand):
    """Django management command entry point"""
    
    help = "Train LightGBM model for itinerary ranking"
    
    def add_arguments(self, parser):
        """Define command arguments"""
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print verbose output during training',
        )
        parser.add_argument(
            '--city',
            type=str,
            default='Lahore',
            help='City to train on (default: Lahore)',
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=None,
            help='Limit to N itineraries (for quick testing)',
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Load and test existing model without training',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Custom output path for model (default: backend/ml_models/itinerary_ranker.pkl)',
        )
    
    def handle(self, *args, **options):
        """Execute command"""
        try:
            verbose = options.get('verbose', False)
            city = options.get('city', 'Lahore')
            sample_limit = options.get('sample')
            test_only = options.get('test_only', False)
            output_path = options.get('output') or os.path.join(
                settings.BASE_DIR.parent,
                'backend',
                'ml_models',
                'itinerary_ranker.pkl'
            )
            
            # Make output path absolute if relative
            if not os.path.isabs(output_path):
                output_path = os.path.join(settings.BASE_DIR, output_path)
            
            trainer = RankerModelTrainer(verbose=verbose, test_mode=test_only)
            
            if test_only:
                # Load and test existing model
                if trainer.load_model(output_path):
                    self.stdout.write(self.style.SUCCESS(
                        f"\n[OK] Model loaded successfully from {output_path}\n"
                    ))
                else:
                    raise CommandError(f"Failed to load model from {output_path}")
            
            else:
                # Full training pipeline
                self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                self.stdout.write(self.style.SUCCESS("AI Itinerary Ranker Training"))
                self.stdout.write(self.style.SUCCESS("="*60))
                
                # Step 1: Collect data
                samples, report = trainer.collect_data(city=city, limit=sample_limit)
                
                if len(samples) < 100:
                    raise CommandError(
                        f"Insufficient data: {len(samples)} samples. Need at least 100."
                    )
                
                # Step 2: Extract features
                X, y = trainer.extract_features(samples)
                
                # Step 3: Split data
                trainer._log("Splitting data into train/test sets...")
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y,
                    test_size=0.2,
                    random_state=42,
                )
                trainer._log(f"  [OK] Train: {X_train.shape[0]} samples")
                trainer._log(f"  [OK] Test:  {X_test.shape[0]} samples")
                
                # Step 4: Train model
                metrics = trainer.train(X_train, y_train, X_test, y_test)
                
                # Step 5: Evaluate
                trainer.evaluate(metrics)
                
                # Step 6: Save model
                trainer.save_model(output_path)
                
                # Step 7: Success message
                self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                self.stdout.write(self.style.SUCCESS("[OK] Model trained successfully"))
                self.stdout.write(self.style.SUCCESS("[OK] Model saved successfully"))
                self.stdout.write(self.style.SUCCESS("="*60 + "\n"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[FAIL] Error: {str(e)}\n"))
            raise CommandError(str(e))
