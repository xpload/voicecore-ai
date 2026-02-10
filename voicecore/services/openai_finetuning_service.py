"""
OpenAI Fine-tuning Service for VoiceCore AI 2.0.

Provides custom model fine-tuning capabilities for tenant-specific AI customization.
"""

import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

import openai
from openai import OpenAI

from voicecore.config import settings
from voicecore.database import get_db_session, set_tenant_context
from voicecore.logging import get_logger
from voicecore.services.cache_service import cache_service

logger = get_logger(__name__)


class FineTuningStatus(Enum):
    """Fine-tuning job status."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OpenAIFineTuningService:
    """
    Service for managing OpenAI model fine-tuning.
    
    Enables tenant-specific AI customization through fine-tuning on
    conversation data and custom training examples.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.logger = logger
        self.base_model = "gpt-4o-2024-08-06"  # Latest fine-tunable model
    
    async def create_fine_tuning_job(
        self,
        tenant_id: uuid.UUID,
        training_file_id: str,
        validation_file_id: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new fine-tuning job.
        
        Args:
            tenant_id: Tenant UUID
            training_file_id: OpenAI file ID for training data
            validation_file_id: Optional validation file ID
            hyperparameters: Optional hyperparameters (n_epochs, batch_size, learning_rate_multiplier)
            suffix: Optional model name suffix
            
        Returns:
            Dict with job details
        """
        try:
            # Default hyperparameters
            if not hyperparameters:
                hyperparameters = {
                    "n_epochs": 3,
                    "batch_size": "auto",
                    "learning_rate_multiplier": "auto"
                }
            
            # Create fine-tuning job
            job = self.client.fine_tuning.jobs.create(
                training_file=training_file_id,
                validation_file=validation_file_id,
                model=self.base_model,
                hyperparameters=hyperparameters,
                suffix=suffix or f"voicecore-{str(tenant_id)[:8]}"
            )
            
            # Store job info in database
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                await session.execute(
                    """
                    INSERT INTO ai_training_sessions 
                    (tenant_id, job_id, status, training_file_id, validation_file_id, 
                     hyperparameters, created_at)
                    VALUES (:tenant_id, :job_id, :status, :training_file_id, 
                            :validation_file_id, :hyperparameters, :created_at)
                    """,
                    {
                        "tenant_id": tenant_id,
                        "job_id": job.id,
                        "status": job.status,
                        "training_file_id": training_file_id,
                        "validation_file_id": validation_file_id,
                        "hyperparameters": json.dumps(hyperparameters),
                        "created_at": datetime.utcnow()
                    }
                )
                await session.commit()
            
            self.logger.info(
                "Fine-tuning job created",
                tenant_id=str(tenant_id),
                job_id=job.id,
                model=self.base_model
            )
            
            return {
                "job_id": job.id,
                "status": job.status,
                "model": self.base_model,
                "created_at": job.created_at,
                "training_file": training_file_id
            }
            
        except Exception as e:
            self.logger.error("Failed to create fine-tuning job", error=str(e))
            raise
    
    async def upload_training_data(
        self,
        tenant_id: uuid.UUID,
        training_examples: List[Dict[str, Any]]
    ) -> str:
        """
        Upload training data to OpenAI.
        
        Args:
            tenant_id: Tenant UUID
            training_examples: List of training examples in JSONL format
            
        Returns:
            str: OpenAI file ID
        """
        try:
            # Convert to JSONL format
            jsonl_content = "\n".join([json.dumps(example) for example in training_examples])
            
            # Create temporary file
            filename = f"training_data_{tenant_id}_{datetime.utcnow().timestamp()}.jsonl"
            
            # Upload to OpenAI
            file_response = self.client.files.create(
                file=jsonl_content.encode('utf-8'),
                purpose="fine-tune"
            )
            
            self.logger.info(
                "Training data uploaded",
                tenant_id=str(tenant_id),
                file_id=file_response.id,
                examples_count=len(training_examples)
            )
            
            return file_response.id
            
        except Exception as e:
            self.logger.error("Failed to upload training data", error=str(e))
            raise
    
    async def prepare_training_data_from_conversations(
        self,
        tenant_id: uuid.UUID,
        min_rating: int = 4,
        max_examples: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Prepare training data from successful conversations.
        
        Args:
            tenant_id: Tenant UUID
            min_rating: Minimum conversation rating to include
            max_examples: Maximum number of examples
            
        Returns:
            List of training examples
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                # Get successful conversations with high ratings
                result = await session.execute(
                    """
                    SELECT c.id, c.transcript, f.rating, f.feedback_text
                    FROM calls c
                    JOIN ai_feedback f ON c.id = f.call_id
                    WHERE c.tenant_id = :tenant_id
                      AND f.rating >= :min_rating
                      AND c.transcript IS NOT NULL
                    ORDER BY f.rating DESC, c.created_at DESC
                    LIMIT :max_examples
                    """,
                    {
                        "tenant_id": tenant_id,
                        "min_rating": min_rating,
                        "max_examples": max_examples
                    }
                )
                
                conversations = result.fetchall()
                
                # Convert to training format
                training_examples = []
                for conv in conversations:
                    transcript = json.loads(conv[1]) if isinstance(conv[1], str) else conv[1]
                    
                    # Format as chat completion
                    messages = []
                    for turn in transcript:
                        messages.append({
                            "role": turn.get("role", "user"),
                            "content": turn.get("content", "")
                        })
                    
                    training_examples.append({
                        "messages": messages
                    })
                
                self.logger.info(
                    "Training data prepared from conversations",
                    tenant_id=str(tenant_id),
                    examples_count=len(training_examples)
                )
                
                return training_examples
                
        except Exception as e:
            self.logger.error("Failed to prepare training data", error=str(e))
            raise
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get fine-tuning job status.
        
        Args:
            job_id: OpenAI job ID
            
        Returns:
            Dict with job status
        """
        try:
            # Check cache first
            cache_key = f"finetuning_job:{job_id}"
            cached = await cache_service.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Get from OpenAI
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            
            result = {
                "job_id": job.id,
                "status": job.status,
                "model": job.model,
                "fine_tuned_model": job.fine_tuned_model,
                "created_at": job.created_at,
                "finished_at": job.finished_at,
                "trained_tokens": job.trained_tokens,
                "error": job.error.message if job.error else None
            }
            
            # Cache for 5 minutes if not completed
            if job.status in ["queued", "running"]:
                await cache_service.set(cache_key, json.dumps(result), ttl=300)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to get job status", job_id=job_id, error=str(e))
            raise
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a fine-tuning job.
        
        Args:
            job_id: OpenAI job ID
            
        Returns:
            bool: True if cancelled successfully
        """
        try:
            self.client.fine_tuning.jobs.cancel(job_id)
            
            self.logger.info("Fine-tuning job cancelled", job_id=job_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            return False
    
    async def list_tenant_models(self, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        List all fine-tuned models for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            List of model details
        """
        try:
            async with get_db_session() as session:
                await set_tenant_context(session, str(tenant_id))
                
                result = await session.execute(
                    """
                    SELECT job_id, status, fine_tuned_model, created_at, finished_at
                    FROM ai_training_sessions
                    WHERE tenant_id = :tenant_id
                      AND status = 'succeeded'
                    ORDER BY finished_at DESC
                    """,
                    {"tenant_id": tenant_id}
                )
                
                models = []
                for row in result.fetchall():
                    models.append({
                        "job_id": row[0],
                        "status": row[1],
                        "model_id": row[2],
                        "created_at": row[3].isoformat() if row[3] else None,
                        "finished_at": row[4].isoformat() if row[4] else None
                    })
                
                return models
                
        except Exception as e:
            self.logger.error("Failed to list tenant models", error=str(e))
            raise
    
    async def delete_fine_tuned_model(self, model_id: str) -> bool:
        """
        Delete a fine-tuned model.
        
        Args:
            model_id: OpenAI model ID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            self.client.models.delete(model_id)
            
            self.logger.info("Fine-tuned model deleted", model_id=model_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete model", model_id=model_id, error=str(e))
            return False
    
    async def get_training_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get training metrics for a completed job.
        
        Args:
            job_id: OpenAI job ID
            
        Returns:
            Dict with training metrics or None
        """
        try:
            # Get job events
            events = self.client.fine_tuning.jobs.list_events(job_id, limit=100)
            
            metrics = {
                "training_loss": [],
                "validation_loss": [],
                "training_accuracy": [],
                "validation_accuracy": []
            }
            
            for event in events.data:
                if event.type == "metrics":
                    data = event.data
                    if "training_loss" in data:
                        metrics["training_loss"].append(data["training_loss"])
                    if "validation_loss" in data:
                        metrics["validation_loss"].append(data["validation_loss"])
                    if "training_accuracy" in data:
                        metrics["training_accuracy"].append(data["training_accuracy"])
                    if "validation_accuracy" in data:
                        metrics["validation_accuracy"].append(data["validation_accuracy"])
            
            return metrics if any(metrics.values()) else None
            
        except Exception as e:
            self.logger.error("Failed to get training metrics", job_id=job_id, error=str(e))
            return None


# Global instance
finetuning_service = OpenAIFineTuningService()
