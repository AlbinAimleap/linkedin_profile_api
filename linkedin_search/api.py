from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Dict, Any, List, Literal, Union
import uuid
import json
from datetime import datetime
from linkedin_search.scraper import get_profile, get_multiple_profiles, Profile, Error
from linkedin_search.serp import SearchOrchestrator, SerperDevService
from linkedin_search.tasks import Task
from dotenv import load_dotenv
import os
import logging
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

def error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return ApiResponse(
                success=False,
                message=f"An error occurred: {str(e)}",
                data={"error": str(e), "error_type": type(e).__name__}
            )
    return wrapper

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'dict') and callable(obj.dict):  # For Pydantic models
            return obj.dict()
        return super().default(obj)


class ApiResponse(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    data: Optional[dict] = None

class SearchService:
    def __init__(self):
        try:
            self.orchestrator = SearchOrchestrator()
            self.serp_service = SerperDevService(api_key=os.getenv("SERPER_API_KEY"))
            if not os.getenv("SERPER_API_KEY"):
                raise ValueError("SERPER_API_KEY environment variable not set")
            self.orchestrator.add_service(self.serp_service)
            logger.info("SearchService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SearchService: {str(e)}", exc_info=True)
            raise

    def get_search_history(self, query: str, _type: str) -> List[Dict]:
        try:
            history = Task.get_search_history(f"{query}_{_type}")
            return json.loads(history) if history else None
        except Exception as e:
            logger.error(f"Error getting search history: {str(e)}", exc_info=True)
            return None

    def save_search_history(self, query: str, items: List[Dict], _type: str):
        try:
            # Convert Pydantic models to dictionaries
            serializable_items = []
            for item in items:
                if hasattr(item, 'dict') and callable(item.dict):
                    serializable_items.append(item.dict())
                else:
                    serializable_items.append(item)
                    
            serialized_items = json.dumps(serializable_items, cls=DateTimeEncoder)
            Task.save_search_history(f"{query}_{_type}", serialized_items)
            logger.info(f"Search history saved for query: {query}, type: {_type}")
        except Exception as e:
            logger.error(f"Error saving search history: {str(e)}", exc_info=True)


    async def search(self, query: str, _type: str = "profile") -> AsyncGenerator[Dict, None]:
        try:
            logger.info(f"Starting search for query: {query}, type: {_type}")
            history_items = self.get_search_history(query, _type)
            if history_items:
                logger.info(f"Found {len(history_items)} items in history")
                for item in history_items:
                    yield item
                return

            urls = await self.orchestrator.search(query)
            if not urls:
                logger.warning(f"No URLs found for query: {query}")
                yield ApiResponse(success=False, message="No urls found")
                return

            items = await get_multiple_profiles(urls)
            for item in items:
                yield item   
                     
            self.save_search_history(query, items, _type)
        except Exception as e:
            logger.error(f"Error in search: {str(e)}", exc_info=True)
            yield ApiResponse(success=False, message=f"Search error: {str(e)}")

    async def _process_result(self, result: str) -> Union[Profile, Error]:
        try:
            return await get_profile(result)
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}", exc_info=True)
            return Error(message=str(e), status_code=500)

class TaskManager:
    @staticmethod
    async def process_scraping_task(task_id: str, query: str, _type: str, search_service: SearchService) -> None:
        try:
            logger.info(f"Processing task {task_id} for query: {query}")
            Task.save(task_id, "processing")
            items = []
            async for item in search_service.search(query, _type):
                items.append(item)
            serialized_items = json.dumps(items, cls=DateTimeEncoder)
            Task.save(task_id, "completed", serialized_items)
            logger.info(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}", exc_info=True)
            Task.save(task_id, "failed", json.dumps({"error": str(e)}))

    @staticmethod
    def get_all_tasks() -> List[Dict]:
        try:
            task_keys = Task.get_all_keys()
            return [
                {
                    "task_id": task_id,
                    "status": task.get('status'),
                    "output": json.loads(task.get('output')) if task and task.get('output') else None
                }
                for task_id in task_keys
                if (task := Task.get(task_id))
            ]
        except Exception as e:
            logger.error(f"Error getting all tasks: {str(e)}", exc_info=True)
            return []

search_service = SearchService()
task_manager = TaskManager()

@app.get("/search", response_model=ApiResponse)
@error_handler
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    logger.info(f"Received search request for query: {query}, type: {_type}")
    items = []
    async for item in search_service.search(query, _type):
        items.append(item)
    
    if not items:
        return ApiResponse(success=False, message="No results found", count=0, data={"items": []})
        
    if isinstance(items[0], ApiResponse) and not items[0].success:
        return items[0]
    
    error_items = [item for item in items if isinstance(item, Error)]
    if error_items:
        return ApiResponse(
            success=False,
            message=error_items[0].message,
            count=0,
            data={"error_code": error_items[0].status_code}
        )

    return ApiResponse(
        success=True,
        message="Data retrieved successfully",
        count=len(items),
        data={"items": items}
    )

@app.get("/queue", response_model=ApiResponse)
@error_handler
async def queue_scraping(
    query: str,
    _type: Literal["profile", "company"] = "profile",
    background_tasks: BackgroundTasks = None
) -> ApiResponse:
    logger.info(f"Received queue request for query: {query}, type: {_type}")
    if not query:
        return ApiResponse(
            success=False,
            message="Query parameter is required",
            data={"error": "Missing query parameter"}
        )
        
    if not search_service:
        return ApiResponse(
            success=False,
            message="Search service is not available",
            data={"error": "Service configuration error"}
        )

    task_id = str(uuid.uuid4())
    Task.save(task_id, "queued")
    background_tasks.add_task(task_manager.process_scraping_task, task_id, query, _type, search_service)
    
    return ApiResponse(
        success=True,
        message="Task queued successfully",
        data={
            "task_id": task_id,
            "status": "queued",
            "query": query,
            "type": _type
        }
    )

@app.get("/tasks/{task_id}", response_model=ApiResponse)
@error_handler
async def get_task(task_id: str) -> ApiResponse:
    logger.info(f"Retrieving task with ID: {task_id}")
    
    if not task_id:
        return ApiResponse(
            success=False,
            message="Task ID is required",
            data={"error": "Missing task ID"}
        )
    
    task = task_manager.get_task(task_id)
    if not task:
        return ApiResponse(
            success=False,
            message="Task not found",
            data={"error": f"No task found with ID: {task_id}"}
        )
    
    return ApiResponse(
        success=True,
        message="Task retrieved successfully",
        data={"items": task}
    )


@app.get("/tasks", response_model=ApiResponse)
@error_handler
async def get_tasks():
    logger.info("Retrieving all tasks")
    tasks = task_manager.get_all_tasks()
    return ApiResponse(
        success=True,
        message="Tasks retrieved successfully",
        data={"tasks": tasks}
    )