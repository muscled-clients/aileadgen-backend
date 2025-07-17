"""
Workflow Service - Manages email automation workflows
Handles workflow creation, storage, execution, and management
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from utils.logger import logger, log_business_event

class WorkflowStep(BaseModel):
    """Individual step in a workflow"""
    id: str
    template_id: str
    delay_days: int = 0
    delay_hours: int = 0
    conditions: Dict[str, Any] = {}
    order: int

class EmailWorkflow(BaseModel):
    """Email workflow model"""
    id: str
    name: str
    description: str = ""
    trigger_type: str  # "new_lead", "qualified", "form_incomplete", etc.
    target_audience: str = "all_leads"  # "all_leads", "qualified_leads", "real_estate", etc.
    status: str = "active"  # "active", "paused", "draft"
    steps: List[WorkflowStep] = []
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Statistics
    total_triggered: int = 0
    emails_sent: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    last_activity: Optional[datetime] = None

class WorkflowExecution(BaseModel):
    """Workflow execution instance for a specific lead"""
    id: str
    workflow_id: str
    lead_id: str
    status: str = "active"  # "active", "completed", "paused", "failed"
    current_step: int = 0
    next_execution: Optional[datetime] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    last_email_sent: Optional[datetime] = None

class WorkflowService:
    """Service for managing email workflows"""
    
    def __init__(self):
        self.workflows_file = "database/workflows.json"
        self.executions_file = "database/workflow_executions.json"
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure required JSON files exist"""
        for file_path in [self.workflows_file, self.executions_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def _load_workflows(self) -> List[EmailWorkflow]:
        """Load workflows from JSON file"""
        try:
            with open(self.workflows_file, 'r') as f:
                data = json.load(f)
                return [EmailWorkflow(**workflow) for workflow in data]
        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
            return []
    
    def _save_workflows(self, workflows: List[EmailWorkflow]):
        """Save workflows to JSON file"""
        try:
            with open(self.workflows_file, 'w') as f:
                json.dump([workflow.dict() for workflow in workflows], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving workflows: {e}")
    
    def _load_executions(self) -> List[WorkflowExecution]:
        """Load workflow executions from JSON file"""
        try:
            with open(self.executions_file, 'r') as f:
                data = json.load(f)
                return [WorkflowExecution(**execution) for execution in data]
        except Exception as e:
            logger.error(f"Error loading workflow executions: {e}")
            return []
    
    def _save_executions(self, executions: List[WorkflowExecution]):
        """Save workflow executions to JSON file"""
        try:
            with open(self.executions_file, 'w') as f:
                json.dump([execution.dict() for execution in executions], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving workflow executions: {e}")
    
    async def create_workflow(self, workflow_data: Dict) -> EmailWorkflow:
        """Create a new email workflow"""
        try:
            # Generate workflow ID
            workflow_id = f"workflow_{len(self._load_workflows()) + 1}_{int(datetime.utcnow().timestamp())}"
            
            # Create workflow steps
            steps = []
            step_data = workflow_data.get("steps", [])
            for i, step in enumerate(step_data):
                step_obj = WorkflowStep(
                    id=f"step_{i+1}_{workflow_id}",
                    template_id=step.get("template_id", ""),
                    delay_days=step.get("delay_days", 0),
                    delay_hours=step.get("delay_hours", 0),
                    conditions=step.get("conditions", {}),
                    order=i + 1
                )
                steps.append(step_obj)
            
            # Create workflow
            workflow = EmailWorkflow(
                id=workflow_id,
                name=workflow_data.get("name", ""),
                description=workflow_data.get("description", ""),
                trigger_type=workflow_data.get("trigger_type", "manual"),
                target_audience=workflow_data.get("target_audience", "all_leads"),
                status=workflow_data.get("status", "active"),
                steps=steps,
                settings=workflow_data.get("settings", {})
            )
            
            # Save to database
            workflows = self._load_workflows()
            workflows.append(workflow)
            self._save_workflows(workflows)
            
            log_business_event(
                event="workflow_created",
                entity_type="workflow",
                entity_id=workflow.id,
                details={"name": workflow.name, "trigger_type": workflow.trigger_type, "steps": len(workflow.steps)}
            )
            
            logger.info(f"Created email workflow: {workflow.id}")
            return workflow
            
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            raise
    
    async def get_workflow(self, workflow_id: str) -> Optional[EmailWorkflow]:
        """Get workflow by ID"""
        workflows = self._load_workflows()
        for workflow in workflows:
            if workflow.id == workflow_id:
                return workflow
        return None
    
    async def get_workflows(self, trigger_type: str = None, status: str = None) -> List[EmailWorkflow]:
        """Get all workflows with optional filtering"""
        workflows = self._load_workflows()
        
        if trigger_type:
            workflows = [w for w in workflows if w.trigger_type == trigger_type]
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        return workflows
    
    async def update_workflow(self, workflow_id: str, workflow_data: Dict) -> Optional[EmailWorkflow]:
        """Update an existing workflow"""
        try:
            workflows = self._load_workflows()
            
            for i, workflow in enumerate(workflows):
                if workflow.id == workflow_id:
                    # Update workflow fields
                    workflow.name = workflow_data.get("name", workflow.name)
                    workflow.description = workflow_data.get("description", workflow.description)
                    workflow.trigger_type = workflow_data.get("trigger_type", workflow.trigger_type)
                    workflow.target_audience = workflow_data.get("target_audience", workflow.target_audience)
                    workflow.status = workflow_data.get("status", workflow.status)
                    workflow.settings = workflow_data.get("settings", workflow.settings)
                    workflow.updated_at = datetime.utcnow()
                    
                    # Update steps if provided
                    if "steps" in workflow_data:
                        steps = []
                        step_data = workflow_data["steps"]
                        for j, step in enumerate(step_data):
                            step_obj = WorkflowStep(
                                id=step.get("id", f"step_{j+1}_{workflow_id}"),
                                template_id=step.get("template_id", ""),
                                delay_days=step.get("delay_days", 0),
                                delay_hours=step.get("delay_hours", 0),
                                conditions=step.get("conditions", {}),
                                order=j + 1
                            )
                            steps.append(step_obj)
                        workflow.steps = steps
                    
                    workflows[i] = workflow
                    self._save_workflows(workflows)
                    
                    logger.info(f"Updated workflow: {workflow_id}")
                    return workflow
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating workflow: {e}")
            raise
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        try:
            workflows = self._load_workflows()
            original_count = len(workflows)
            
            workflows = [w for w in workflows if w.id != workflow_id]
            
            if len(workflows) < original_count:
                self._save_workflows(workflows)
                
                # Also delete associated executions
                executions = self._load_executions()
                executions = [e for e in executions if e.workflow_id != workflow_id]
                self._save_executions(executions)
                
                logger.info(f"Deleted workflow: {workflow_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            return False
    
    async def pause_workflow(self, workflow_id: str) -> Optional[EmailWorkflow]:
        """Pause a workflow"""
        return await self.update_workflow(workflow_id, {"status": "paused"})
    
    async def activate_workflow(self, workflow_id: str) -> Optional[EmailWorkflow]:
        """Activate a workflow"""
        return await self.update_workflow(workflow_id, {"status": "active"})
    
    async def trigger_workflow(self, workflow_id: str, lead_id: str) -> bool:
        """Trigger a workflow for a specific lead"""
        try:
            workflow = await self.get_workflow(workflow_id)
            if not workflow or workflow.status != "active":
                logger.warning(f"Workflow not found or not active: {workflow_id}")
                return False
            
            # Check if there's already an active execution for this lead
            executions = self._load_executions()
            existing_execution = next((e for e in executions 
                                     if e.workflow_id == workflow_id and e.lead_id == lead_id 
                                     and e.status == "active"), None)
            
            if existing_execution:
                logger.info(f"Workflow already active for lead: {workflow_id}, {lead_id}")
                return True
            
            # Create new execution
            execution_id = f"exec_{workflow_id}_{lead_id}_{int(datetime.utcnow().timestamp())}"
            
            # Calculate next execution time (for first step)
            next_execution = datetime.utcnow()
            if workflow.steps and workflow.steps[0].delay_days > 0:
                next_execution += timedelta(days=workflow.steps[0].delay_days)
            if workflow.steps and workflow.steps[0].delay_hours > 0:
                next_execution += timedelta(hours=workflow.steps[0].delay_hours)
            
            execution = WorkflowExecution(
                id=execution_id,
                workflow_id=workflow_id,
                lead_id=lead_id,
                status="active",
                current_step=0,
                next_execution=next_execution
            )
            
            executions.append(execution)
            self._save_executions(executions)
            
            # Update workflow stats
            workflow.total_triggered += 1
            workflow.last_activity = datetime.utcnow()
            await self.update_workflow(workflow_id, {
                "total_triggered": workflow.total_triggered,
                "last_activity": workflow.last_activity
            })
            
            log_business_event(
                event="workflow_triggered",
                entity_type="workflow",
                entity_id=workflow_id,
                details={"lead_id": lead_id, "execution_id": execution_id}
            )
            
            logger.info(f"Triggered workflow {workflow_id} for lead {lead_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering workflow: {e}")
            return False
    
    async def get_pending_executions(self) -> List[WorkflowExecution]:
        """Get workflow executions that are ready to run"""
        try:
            executions = self._load_executions()
            now = datetime.utcnow()
            
            pending = []
            for execution in executions:
                if (execution.status == "active" and 
                    execution.next_execution and 
                    execution.next_execution <= now):
                    pending.append(execution)
            
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending executions: {e}")
            return []
    
    async def complete_execution_step(self, execution_id: str, success: bool = True) -> bool:
        """Mark an execution step as completed and schedule next step"""
        try:
            executions = self._load_executions()
            
            for i, execution in enumerate(executions):
                if execution.id == execution_id:
                    workflow = await self.get_workflow(execution.workflow_id)
                    if not workflow:
                        logger.error(f"Workflow not found: {execution.workflow_id}")
                        return False
                    
                    execution.last_email_sent = datetime.utcnow()
                    
                    if success:
                        # Move to next step
                        execution.current_step += 1
                        
                        if execution.current_step >= len(workflow.steps):
                            # Workflow completed
                            execution.status = "completed"
                            execution.completed_at = datetime.utcnow()
                            execution.next_execution = None
                        else:
                            # Schedule next step
                            next_step = workflow.steps[execution.current_step]
                            next_execution = datetime.utcnow()
                            
                            if next_step.delay_days > 0:
                                next_execution += timedelta(days=next_step.delay_days)
                            if next_step.delay_hours > 0:
                                next_execution += timedelta(hours=next_step.delay_hours)
                            
                            execution.next_execution = next_execution
                    else:
                        # Failed step
                        execution.status = "failed"
                        execution.next_execution = None
                    
                    executions[i] = execution
                    self._save_executions(executions)
                    
                    logger.info(f"Completed execution step: {execution_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error completing execution step: {e}")
            return False
    
    async def get_workflow_stats(self) -> Dict:
        """Get workflow statistics"""
        try:
            workflows = self._load_workflows()
            executions = self._load_executions()
            
            stats = {
                "total_workflows": len(workflows),
                "active_workflows": len([w for w in workflows if w.status == "active"]),
                "paused_workflows": len([w for w in workflows if w.status == "paused"]),
                "total_executions": len(executions),
                "active_executions": len([e for e in executions if e.status == "active"]),
                "completed_executions": len([e for e in executions if e.status == "completed"]),
                "failed_executions": len([e for e in executions if e.status == "failed"])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting workflow stats: {e}")
            return {}
    
    async def get_lead_workflow_executions(self, lead_id: str) -> List[WorkflowExecution]:
        """Get all workflow executions for a specific lead"""
        try:
            executions = self._load_executions()
            return [e for e in executions if e.lead_id == lead_id]
        except Exception as e:
            logger.error(f"Error getting lead workflow executions: {e}")
            return []