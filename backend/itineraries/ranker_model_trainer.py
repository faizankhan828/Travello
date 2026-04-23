"""
Model trainer for the itinerary ranker.
Trains LightGBM model using real or synthetic data.
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import numpy as np

try:
    import lightgbm as lgb
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("LightGBM or sklearn not available")

from .ranker_data_analyzer import RankerDataAnalyzer, DataSample
from .feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


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
    FEATURE_COLUMNS = FeatureExtractor.FEATURE_COLUMNS
    
    def __init__(self, verbose: bool = False):
        """Initialize trainer"""
        if not LIGHTGBM_AVAILABLE:
            raise RuntimeError("LightGBM and sklearn are required for training")
        
        self.verbose = verbose
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
    
    def collect_data(self, city: str = 'Lahore', 
                    limit: Optional[int] = None,
                    use_synthetic: bool = True) -> Tuple[List[DataSample], Dict]:
        """
        Collect training data.
        
        Args:
            city: City to train on
            limit: Maximum number of real itineraries
            use_synthetic: If no real data, generate synthetic samples
        
        Returns:
            Tuple of (samples, report)
        """
        self._log(f"Collecting training data for {city}...")
        
        analyzer = RankerDataAnalyzer(verbose=self.verbose)
        report = analyzer.analyze(city=city, limit=limit)
        
        # Log summary
        summary = report['data_overview']
        self._log(f"  [OK] Real data: {summary['total_training_samples']} samples")
        self._log(f"    - Positive: {summary['positive_samples']}")
        self._log(f"    - Negative: {summary['negative_samples']}")
        
        # Use synthetic data if needed
        samples = analyzer.samples
        if len(samples) == 0:
            self._log("  [INFO] No real data found, generating synthetic samples...")
            if use_synthetic:
                samples = analyzer.generate_synthetic_data(samples_per_combination=5)
                self._log(f"  [OK] Generated {len(samples)} synthetic samples")
            else:
                raise ValueError("No real data and synthetic disabled")
        
        return samples, report
    
    def train(self, samples: List[DataSample],
              test_size: float = 0.2,
              random_state: int = 42) -> Dict:
        """
        Train LightGBM model from samples.
        
        Args:
            samples: List of DataSample objects
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility
        
        Returns:
            Dictionary with training metrics
        """
        if not samples:
            raise ValueError("No training samples provided")
        
        self._log("Training LightGBM model...")
        
        # Extract features
        X, y = FeatureExtractor.extract_features(samples)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        self._log(f"  Split data: {len(X_train)} train, {len(X_test)} test")
        
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
            'objective': 'regression',
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
                lgb.log_evaluation(period=0) if self.verbose else None,
            ],
        )
        
        # Evaluate
        self._log("  [OK] Model training complete")
        
        # Get predictions
        y_train_pred = self.model.predict(X_train_scaled)
        y_test_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'train_rmse': float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
            'test_rmse': float(np.sqrt(mean_squared_error(y_test, y_test_pred))),
            'train_mae': float(mean_absolute_error(y_train, y_train_pred)),
            'test_mae': float(mean_absolute_error(y_test, y_test_pred)),
            'train_r2': float(r2_score(y_train, y_train_pred)),
            'test_r2': float(r2_score(y_test, y_test_pred)),
            'n_boosting_rounds': self.model.num_trees(),
            'n_features': X.shape[1],
            'n_train_samples': len(X_train),
            'n_test_samples': len(X_test),
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
        for rank, idx in enumerate(top_features_idx, 1):
            if idx < len(self.FEATURE_COLUMNS):
                feature_name = self.FEATURE_COLUMNS[idx]
                importance = feature_importance[idx]
                self._log(f"  {rank}. {feature_name}: {importance:.0f}")
    
    def save_model(self, output_path: str) -> str:
        """
        Save trained model and scaler to disk.
        
        Args:
            output_path: Path to save model (e.g., backend/ml_models/itinerary_ranker.pkl)
        
        Returns:
            Full path to saved model
        """
        if not self.model or not self.scaler:
            raise ValueError("Model not trained yet")
        
        self._log(f"Saving model to {output_path}...")
        
        # Create directory if needed
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
                'lightgbm': lgb.__version__ if LIGHTGBM_AVAILABLE else 'N/A',
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
    
    def full_train_pipeline(self, city: str = 'Lahore',
                           output_path: str = 'ml_models/itinerary_ranker.pkl',
                           use_synthetic: bool = True) -> Dict:
        """
        Run complete training pipeline: collect -> train -> save -> evaluate.
        
        Args:
            city: City to train on
            output_path: Where to save model
            use_synthetic: Use synthetic data if real data unavailable
        
        Returns:
            Dictionary with training summary
        """
        try:
            # Collect data
            samples, data_report = self.collect_data(city, use_synthetic=use_synthetic)
            
            # Train model
            metrics = self.train(samples)
            
            # Evaluate
            self.evaluate(metrics)
            
            # Save
            saved_path = self.save_model(output_path)
            
            return {
                'status': 'success',
                'model_path': saved_path,
                'metrics': metrics,
                'data_summary': data_report['data_overview'],
            }
        
        except Exception as e:
            self._log(f"Training failed: {str(e)}", level='error')
            raise
