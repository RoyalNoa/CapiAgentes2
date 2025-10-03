"""
API endpoints for AI Workspace functionality
"""

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

from .agents.workspace_agent import WorkspaceAgent
from ..workspace.task_scheduler import TaskPriority, TaskStatus

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/workspace", tags=["workspace"])

class WorkspaceAgentSingleton:
    """Singleton pattern for workspace agent"""
    _instance = None
    
    @classmethod
    def get_instance(cls) -> WorkspaceAgent:
        if cls._instance is None:
            cls._instance = WorkspaceAgent("ai_workspace")
        return cls._instance

def get_workspace_agent() -> WorkspaceAgent:
    """Get workspace agent instance using singleton pattern"""
    return WorkspaceAgentSingleton.get_instance()


@router.on_event("startup")
async def startup_workspace():
    """Initialize workspace on startup"""
    try:
        get_workspace_agent()
        logger.info("AI Workspace initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing AI Workspace: {e}")


@router.on_event("shutdown")
async def shutdown_workspace():
    """Cleanup workspace on shutdown"""
    try:
        agent = get_workspace_agent()
        if hasattr(agent, 'task_scheduler'):
            agent.task_scheduler.stop_scheduler()
        logger.info("AI Workspace shutdown completed")
    except Exception as e:
        logger.error(f"Error during workspace shutdown: {e}")


# =============================================================================
# FILE MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/files/analysis")
async def create_analysis_file(
    analysis_data: Dict[str, Any] = Body(...),
    filename: Optional[str] = Body(None),
    file_type: str = Body("json")
):
    """Create and save an analysis file"""
    try:
        agent = get_workspace_agent()
        result = agent.create_analysis_file(
            analysis_data=analysis_data,
            filename=filename,
            file_type=file_type
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error creating analysis file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_files(
    directory: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    include_metadata: bool = Query(True),
    limit: int = Query(50)
):
    """List files in the workspace"""
    try:
        agent = get_workspace_agent()
        files = agent.file_manager.list_files(
            directory=directory,
            file_type=file_type,
            include_metadata=include_metadata
        )
        return JSONResponse(content={"files": files[:limit], "total": len(files)})
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/stats")
async def get_workspace_stats():
    """Get workspace file statistics"""
    try:
        agent = get_workspace_agent()
        stats = agent.file_manager.get_workspace_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting workspace stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_path:path}")
async def delete_file(file_path: str):
    """Delete a file from workspace"""
    try:
        agent = get_workspace_agent()
        success = agent.file_manager.delete_file(file_path)
        if success:
            return JSONResponse(content={"message": f"File {file_path} deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KNOWLEDGE BASE ENDPOINTS
# =============================================================================

@router.post("/knowledge/documents")
async def add_document(
    doc_id: str = Body(...),
    content: str = Body(...),
    title: Optional[str] = Body(None),
    doc_type: str = Body("general"),
    file_path: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None)
):
    """Add a document to the knowledge base"""
    try:
        agent = get_workspace_agent()
        result = agent.knowledge_base.add_document(
            doc_id=doc_id,
            content=content,
            title=title,
            doc_type=doc_type,
            file_path=file_path,
            metadata=metadata
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/search")
async def search_documents(
    query: str = Query(...),
    limit: int = Query(10),
    doc_type: Optional[str] = Query(None),
    days_back: Optional[int] = Query(None)
):
    """Search documents in knowledge base"""
    try:
        agent = get_workspace_agent()
        results = agent.knowledge_base.search_documents(
            query=query,
            limit=limit,
            doc_type=doc_type,
            days_back=days_back
        )
        return JSONResponse(content={"results": results, "total": len(results)})
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a specific document by ID"""
    try:
        agent = get_workspace_agent()
        document = agent.knowledge_base.get_document(doc_id)
        if document:
            return JSONResponse(content=document)
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/documents")
async def list_documents(
    doc_type: Optional[str] = Query(None),
    limit: int = Query(50),
    days_back: Optional[int] = Query(None)
):
    """List documents in knowledge base"""
    try:
        agent = get_workspace_agent()
        documents = agent.knowledge_base.list_documents(
            doc_type=doc_type,
            limit=limit,
            days_back=days_back
        )
        return JSONResponse(content={"documents": documents, "total": len(documents)})
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from knowledge base"""
    try:
        agent = get_workspace_agent()
        success = agent.knowledge_base.delete_document(doc_id)
        if success:
            return JSONResponse(content={"message": f"Document {doc_id} deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge base statistics"""
    try:
        agent = get_workspace_agent()
        stats = agent.knowledge_base.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/reindex")
async def reindex_knowledge_base():
    """Reindex knowledge base for improved search"""
    try:
        agent = get_workspace_agent()
        result = agent.knowledge_base.reindex_documents()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error reindexing knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MEMORY MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/memory/conversations")
async def store_conversation(
    session_id: str = Body(...),
    messages: List[Dict[str, Any]] = Body(...),
    metadata: Optional[Dict[str, Any]] = Body(None)
):
    """Store a conversation in memory"""
    try:
        agent = get_workspace_agent()
        result = agent.memory_manager.store_conversation(
            session_id=session_id,
            messages=messages,
            metadata=metadata
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error storing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve a specific conversation"""
    try:
        agent = get_workspace_agent()
        conversation = agent.memory_manager.retrieve_conversation(session_id)
        if conversation:
            return JSONResponse(content=conversation)
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/conversations")
async def list_conversations(
    limit: int = Query(20),
    days_back: int = Query(30)
):
    """List recent conversations"""
    try:
        agent = get_workspace_agent()
        conversations = agent.memory_manager.list_conversations(
            limit=limit,
            days_back=days_back
        )
        return JSONResponse(content={"conversations": conversations, "total": len(conversations)})
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/context")
async def get_context(
    query: str = Query(...),
    session_id: Optional[str] = Query(None),
    limit: int = Query(5),
    time_window_days: int = Query(30)
):
    """Retrieve relevant context from memory"""
    try:
        agent = get_workspace_agent()
        context = agent.memory_manager.retrieve_context(
            query=query,
            session_id=session_id,
            limit=limit,
            time_window_days=time_window_days
        )
        return JSONResponse(content={"context": context, "total": len(context)})
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/conversations/{session_id}/summary")
async def get_conversation_summary(session_id: str):
    """Get a summary of a conversation"""
    try:
        agent = get_workspace_agent()
        summary = agent.memory_manager.get_conversation_summary(session_id)
        if summary:
            return JSONResponse(content=summary)
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        agent = get_workspace_agent()
        stats = agent.memory_manager.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TASK SCHEDULER ENDPOINTS
# =============================================================================

@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """List scheduled tasks"""
    try:
        agent = get_workspace_agent()
        status_filter = TaskStatus(status) if status else None
        tasks = agent.task_scheduler.list_tasks(
            status_filter=status_filter,
            limit=limit
        )
        return JSONResponse(content={"tasks": tasks, "total": len(tasks)})
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        agent = get_workspace_agent()
        task = agent.task_scheduler.get_task_status(task_id)
        if task:
            return JSONResponse(content=task)
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a scheduled task"""
    try:
        agent = get_workspace_agent()
        success = agent.task_scheduler.cancel_task(task_id)
        if success:
            return JSONResponse(content={"message": f"Task {task_id} cancelled successfully"})
        else:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/scheduler/stats")
async def get_scheduler_stats():
    """Get task scheduler statistics"""
    try:
        agent = get_workspace_agent()
        stats = agent.task_scheduler.get_scheduler_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting scheduler stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WORKSPACE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/summary")
async def get_workspace_summary():
    """Get complete workspace summary"""
    try:
        agent = get_workspace_agent()
        summary = agent.get_workspace_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Error getting workspace summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organize")
async def organize_workspace():
    """Organize and optimize workspace"""
    try:
        agent = get_workspace_agent()
        result = agent.organize_knowledge()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error organizing workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(
    template_name: str = Body(...),
    template_content: str = Body(...),
    template_type: str = Body("analysis")
):
    """Create a reusable template"""
    try:
        agent = get_workspace_agent()
        result = agent.create_template(
            template_content=template_content,
            template_name=template_name,
            template_type=template_type
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work/previous")
async def read_previous_work(
    query: str = Query(...),
    limit: int = Query(5)
):
    """Read previous work relevant to a query"""
    try:
        agent = get_workspace_agent()
        results = agent.read_previous_work(query=query, limit=limit)
        return JSONResponse(content={"results": results, "total": len(results)})
    except Exception as e:
        logger.error(f"Error reading previous work: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def workspace_health_check():
    """Health check for workspace system"""
    try:
        agent = get_workspace_agent()
        
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "file_manager": "healthy",
                "memory_manager": "healthy", 
                "knowledge_base": "healthy",
                "task_scheduler": "healthy" if agent.task_scheduler.is_running else "stopped"
            },
            "workspace_root": str(agent.workspace_root),
            "workspace_exists": agent.workspace_root.exists()
        }
        
        return JSONResponse(content=health_status)
    except Exception as e:
        logger.error(f"Workspace health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503
        )

