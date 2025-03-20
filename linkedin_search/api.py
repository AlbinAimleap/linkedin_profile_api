from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Dict, Any, List, Literal, Union
import uuid
import json
from datetime import datetime
from linkedin_search.scraper import LinkedInVoyagerAPI
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
        self.api = LinkedInVoyagerAPI()
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
            items.append(item)
            yield item
            
        self.save_search_history(query, items, _type)

    async def _process_result(self, result: str, _type: str) -> Dict:
        if _type == "profile":
            if result.startswith('http'):
                return self.api.get_profile_by_url(result)
            else:
                return self.api.get_profile_data(result)
        else:
            company = self.api.get_company_data(result)
            return {
                'name': company.name,
                'linkedin_url': company.linkedin_url,
                'pictureLink': company.pictureLink,
                'dateInsert': company.dateInsert,
                'dateUpdate': company.dateUpdate,
                'employees': company.employees,
                'company_logo': company.company_logo,
                'address': company.address,
                'description': company.description,
                'short_description': company.short_description,
                'phone': company.phone,
                'founded_on': company.founded_on
            }

class TaskManager:
    @staticmethod
    async def process_scraping_task(task_id: str, query: str, _type: str, search_service: SearchService) -> None:
        Task.save(task_id, "processing")
        items = [item async for item in search_service.search(query, _type)]
        serialized_items = json.dumps(items, cls=DateTimeEncoder)
        Task.save(task_id, "completed", serialized_items)

    @staticmethod
    def get_all_tasks() -> List[Dict]:
        task_keys = Task.get_all_keys()
        tasks = []
        for task_id in task_keys:
            task = Task.get(task_id)
            if task:
                output = json.loads(task.get('output')) if task.get('output') else None
                tasks.append({
                    "task_id": task_id,
                    "status": task.get('status'),
                    "output": output
                })
        return tasks

search_service = SearchService()
task_manager = TaskManager()

async def create_streaming_response(query: str, _type: Literal["profile", "company"]="profile") -> AsyncGenerator[str, None]:
    async for item in search_service.search(query, _type):
        yield json.dumps({
            "success": True,
            "message": "Data retrieved successfully",
            "data": item
        }, cls=DateTimeEncoder) + "\n"

@app.get("/search", response_model=ApiResponse)
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    # try:
        items = [item async for item in search_service.search(query, _type)]
        if not items:
            return ApiResponse(
                success=True,
                message="No results found",
                count=0,
                data={"items": []}
            )
        
        return ApiResponse(
            success=True,
            message="Data retrieved successfully",
            count=len(items),
            data={"items": items}
        )
    
    # except Exception as e:
    #     return ApiResponse(
    #         success=False,
    #         message=f"Search failed: {str(e)}",
    #         data=None
    #     )

@app.get("/stream", response_class=StreamingResponse)
async def get_profile_stream(query: str, _type: Literal["profile", "company"] = "profile"):
    try:
        return StreamingResponse(
            create_streaming_response(query, _type), 
            media_type="application/x-ndjson"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Streaming failed: {str(e)}",
            data=None
        )

@app.get("/queue", response_model=ApiResponse)
async def queue_scraping(query: str, _type: Literal["profile", "company"] = "profile", background_tasks: BackgroundTasks = None):
    task_id = str(uuid.uuid4())
    Task.save(task_id, "queued")
    background_tasks.add_task(task_manager.process_scraping_task, task_id, query, _type, search_service)
    return ApiResponse(
        success=True,
        message="Task queued successfully",
        data={"task_id": task_id}
    )

@app.get("/tasks", response_model=ApiResponse)
async def get_tasks():
    tasks = task_manager.get_all_tasks()
    return ApiResponse(
        success=True,
        message="Tasks retrieved successfully",
        data={"tasks": tasks}
    )