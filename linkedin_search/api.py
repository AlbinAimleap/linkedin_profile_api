from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Dict, Any, List, Literal, Union
import uuid
import json
from datetime import datetime
from linkedin_search.scraper import get_profile, Profile, Error
from linkedin_search.serp import SearchOrchestrator, SerperDevService
from linkedin_search.tasks import Task
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ApiResponse(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    data: Optional[dict] = None

class SearchService:
    def __init__(self):
        self.orchestrator = SearchOrchestrator()
        self.serp_service = SerperDevService(api_key=os.getenv("SERPER_API_KEY"))
        self.orchestrator.add_service(self.serp_service)

    def get_search_history(self, query: str, _type: str) -> List[Dict]:
        history = Task.get_search_history(f"{query}_{_type}")
        return json.loads(history) if history else None

    def save_search_history(self, query: str, items: List[Dict], _type: str):
        serialized_items = json.dumps(items, cls=DateTimeEncoder)
        Task.save_search_history(f"{query}_{_type}", serialized_items)

    async def search(self, query: str, _type: str = "profile") -> AsyncGenerator[Dict, None]:
        history_items = self.get_search_history(query, _type)
        if history_items:
            for item in history_items:
                yield item
            return

        results = await self.orchestrator.search(query)
        items = []
        
        for result in results:
            item = await self._process_result(result, _type)
            if isinstance(item, Error):
                yield ApiResponse(success=False, message=item.message)
                return
            items.append(item.model_dump())
            yield item   
                     
        self.save_search_history(query, items, _type)

    async def _process_result(self, result: str, _type: str) -> Union[Profile, Error]:
        return await get_profile(result)
           

class TaskManager:
    @staticmethod
    async def process_scraping_task(task_id: str, query: str, _type: str, search_service: SearchService) -> None:
        Task.save(task_id, "processing")
        items = []
        async for item in search_service.search(query, _type):
            items.append(item)
        serialized_items = json.dumps(items, cls=DateTimeEncoder)
        Task.save(task_id, "completed", serialized_items)

    @staticmethod
    def get_all_tasks() -> List[Dict]:
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

search_service = SearchService()
task_manager = TaskManager()


@app.get("/search", response_model=ApiResponse)
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    try:
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
        
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"An error occurred: {str(e)}",
            count=0,
            data={"error": str(e)}
        )

@app.get("/queue", response_model=ApiResponse)
async def queue_scraping(
    query: str,
    _type: Literal["profile", "company"] = "profile",
    background_tasks: BackgroundTasks = None
) -> ApiResponse:
    try:
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
    except Exception as e:
        return ApiResponse(
            success=False,
            message="Failed to queue task",
            data={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

@app.get("/tasks", response_model=ApiResponse)
async def get_tasks():
    tasks = task_manager.get_all_tasks()
    return ApiResponse(
        success=True,
        message="Tasks retrieved successfully",
        data={"tasks": tasks}
    )