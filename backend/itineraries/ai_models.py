"""
AI Itinerary System - Database Models

Adds monitoring and feedback tracking for AI-driven itinerary generation.
Compatible with existing Itinerary model schema.
"""

from django.db import models
from django.contrib.auth.models import User
import json


class AIGenerationLog(models.Model):
    """
    Logs each AI itinerary generation for monitoring and feedback collection.
    
    Used for:
    - Performance monitoring (latency, success rate)
    - User feedback tracking (for retraining)
    - Debugging and analysis
    """
    
    # Core tracking
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(db_index=True)  # User who requested itinerary
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Generation details
    trip_params = models.JSONField(default=dict, help_text="Trip parameters (mood, interests, budget, etc)")
    final_mood = models.CharField(
        max_length=20,
        choices=[
            ('RELAXING', 'Relaxing'),
            ('SPIRITUAL', 'Spiritual'),
            ('HISTORICAL', 'Historical'),
            ('FOODIE', 'Foodie'),
            ('FUN', 'Fun'),
            ('SHOPPING', 'Shopping'),
            ('NATURE', 'Nature'),
            ('ROMANTIC', 'Romantic'),
            ('FAMILY', 'Family'),
        ],
        help_text="Final mood determined by AI"
    )
    
    # Pipeline stages
    stages_log = models.JSONField(
        default=dict,
        help_text="Results from each stage (emotion detection, ML ranking, LLM enhancement)"
    )
    
    # Performance metrics
    generation_latency_ms = models.FloatField(
        default=0,
        help_text="Total generation time in milliseconds"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[('success', 'Success'), ('error', 'Error'), ('fallback', 'Fallback')],
        default='success'
    )
    
    # Itinerary preview
    itinerary_preview = models.JSONField(
        default=dict,
        help_text="Summary of generated itinerary (num_days, num_places, etc)"
    )
    
    # User feedback (collected post-generation)
    user_feedback_score = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="User rating of itinerary (1-5 stars)"
    )
    
    user_comments = models.TextField(
        blank=True,
        help_text="User feedback comments"
    )
    
    # Implicit feedback
    was_used = models.BooleanField(
        null=True,
        help_text="Whether user actually used this itinerary"
    )
    
    booking_conversion = models.BooleanField(
        default=False,
        help_text="Whether user completed booking from this itinerary"
    )
    
    regenerated = models.BooleanField(
        default=False,
        help_text="Whether user regenerated the itinerary (signal of dissatisfaction)"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['final_mood']),
        ]
    
    def __str__(self):
        return f"Generation {self.id} (User {self.user_id}, {self.final_mood}, {self.status})"
    
    def get_emotion_detection_stage(self) -> dict:
        """Get emotion detection stage results"""
        return self.stages_log.get('emotion_detection', {})
    
    def get_ml_ranking_stage(self) -> dict:
        """Get ML ranking stage results"""
        return self.stages_log.get('ml_ranking', {})
    
    def get_llm_enhancement_stage(self) -> dict:
        """Get LLM enhancement stage results"""
        return self.stages_log.get('llm_enhancement', {})
    
    def was_fallback_used(self) -> bool:
        """Check if fallback was used"""
        return self.stages_log.get('fallback_used', False)
    
    def ml_ranking_confidence(self) -> float:
        """Get ML ranking model confidence"""
        ranking_stage = self.get_ml_ranking_stage()
        return ranking_stage.get('model_confidence', 0.0)


class AIModelVersion(models.Model):
    """
    Version control for AI models.
    
    Tracks model releases, retraining, and performance changes.
    """
    
    MODEL_TYPE_CHOICES = [
        ('emotion', 'Emotion Detection'),
        ('ranker', 'Learning-to-Rank'),
        ('llm', 'LLM Enhancement'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
        ('experimental', 'Experimental'),
        ('training', 'Training'),
    ]
    
    # Model identification
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES)
    version_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="e.g., emotion-v1.2.3, ranker-v2.1.0"
    )
    
    # Training info
    created_date = models.DateTimeField(auto_now_add=True)
    training_start_date = models.DateTimeField(null=True, blank=True)
    training_end_date = models.DateTimeField(null=True, blank=True)
    
    # Training metrics
    training_samples = models.IntegerField(null=True, help_text="Number of samples used for training")
    validation_accuracy = models.FloatField(null=True, help_text="Validation accuracy (0-1)")
    validation_ndcg = models.FloatField(null=True, help_text="NDCG score for ranking (0-1)")
    validation_metrics = models.JSONField(default=dict, help_text="Additional validation metrics")
    
    # Metadata
    model_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 path or local path to model file"
    )
    
    config = models.JSONField(
        default=dict,
        help_text="Model hyperparameters and configuration"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='experimental'
    )
    
    notes = models.TextField(blank=True, help_text="Release notes or changes")
    
    # Usage tracking
    usage_count = models.BigIntegerField(default=0, help_text="Number of predictions made with this model")
    last_used = models.DateTimeField(null=True, help_text="Last usage timestamp")
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['model_type', '-created_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.version_id} ({self.status})"
    
    def is_current(self) -> bool:
        """Check if this is the currently active version for its model type"""
        current = AIModelVersion.objects.filter(
            model_type=self.model_type,
            status='active'
        ).order_by('-created_date').first()
        return current == self
    
    def record_usage(self):
        """Record that this model was used for inference"""
        self.usage_count += 1
        self.last_used = models.functions.Now()
        self.save()


class AIUserFeedback(models.Model):
    """
    Explicit user feedback on AI-generated itineraries.
    
    Used for:
    - Direct user satisfaction measurement
    - Training labels for model improvement
    - Identifying model weaknesses
    """
    
    FEEDBACK_TYPE_CHOICES = [
        ('rating', 'Star Rating'),
        ('like_dislike', 'Like/Dislike'),
        ('comment', 'Text Comment'),
        ('regenerate', 'Regenerated Itinerary'),
        ('booking', 'Completed Booking'),
    ]
    
    generation_log = models.OneToOneField(
        AIGenerationLog,
        on_delete=models.CASCADE,
        related_name='user_feedback',
        help_text="Reference to generation event"
    )
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    
    # Explicit feedback
    rating = models.IntegerField(
        null=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="1-5 star rating"
    )
    
    liked = models.BooleanField(
        null=True,
        help_text="True for like, False for dislike, None for not applicable"
    )
    
    comment = models.TextField(
        blank=True,
        help_text="User's detailed feedback"
    )
    
    # Context
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['generation_log', 'feedback_type']),
        ]
    
    def __str__(self):
        return f"Feedback {self.id} (Generation {self.generation_log_id}, {self.feedback_type})"
    
    def get_label_for_training(self) -> float:
        """
        Convert feedback to training label (0-1).
        
        Used for retraining models with real user feedback.
        """
        if self.rating:
            return self.rating / 5.0
        elif self.liked is not None:
            return 1.0 if self.liked else 0.0
        else:
            return 0.5  # Neutral default


class AIRankerTrainingData(models.Model):
    """
    Training samples for learning-to-rank model.
    
    Stores feature vectors and labels for offline retraining.
    """
    
    DATA_SOURCE_CHOICES = [
        ('synthetic', 'Synthetic (from heuristic)'),
        ('user_feedback', 'Real (from user feedback)'),
        ('interaction', 'Implicit (from user interactions)'),
    ]
    
    # Sample identification
    generation_log = models.ForeignKey(
        AIGenerationLog,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Reference to generation event that produced this sample"
    )
    
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES)
    
    # Features (stored as JSON)
    user_mood = models.CharField(max_length=20)
    user_interests = models.JSONField(default=list)
    user_budget = models.CharField(max_length=20)
    
    place_id = models.CharField(max_length=100)
    place_category = models.CharField(max_length=50)
    place_rating = models.FloatField()
    place_popularity = models.FloatField()
    
    context_day_index = models.IntegerField()
    context_time_of_day = models.CharField(max_length=20)
    
    # Label (relevance score)
    relevance_label = models.FloatField(
        help_text="0-1 score indicating how relevant this place was (1=very relevant)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_used_in_training = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['data_source', 'is_used_in_training']),
        ]
    
    def __str__(self):
        return f"TrainingSample {self.id} ({self.data_source}, label={self.relevance_label:.2f})"


# ============================================
# MIGRATION HELPER FUNCTIONS
# ============================================

def create_ai_models_tables():
    """
    Helper function to create AI models tables.
    Run this in a data migration when deploying AI system.
    """
    from django.core.management import call_command
    call_command('migrate', 'itineraries')
