from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Dict, Any, List, Literal, Union
import uuid
import json
from datetime import datetime
from linkedin_search.linkedin import LinkedIn, LinkedInProfile, LinkedInCompany
from linkedin_search.tasks import Task

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
    

def get_search_history(query: str, _type: str) -> List[Union[LinkedInProfile, LinkedInCompany]]:
    history = Task.get_search_history(f"{query}_{_type}")
    if history:
        return [LinkedInProfile(**profile) if _type == "profile" else LinkedInCompany(**profile) for profile in json.loads(history)]
    return None

def save_search_history(query: str, items: List[Union[LinkedInProfile, LinkedInCompany]], _type: str):
    serialized_items = json.dumps([item.model_dump() for item in items], cls=DateTimeEncoder)
    Task.save_search_history(f"{query}_{_type}", serialized_items)

async def search(query: str, _type: str = "profile") -> AsyncGenerator[Union[LinkedInProfile, LinkedInCompany], None]:
    history_items = get_search_history(query, _type)
    if history_items:
        for item in history_items:
            yield item
    else:
        linkedin = LinkedIn()
        items = []
        if _type == "profile":
            async for profile in linkedin.profile(query):
                items.append(profile)
                yield profile
        else:
            async for company in linkedin.company(query):
                items.append(company)
                yield company
        save_search_history(query, items, _type)
        
async def create_streaming_response(query: str, _type: Literal["profile", "company"]="profile") -> AsyncGenerator[str, None]:
    async for item in search(query, _type):
        yield json.dumps({
            "success": True,
            "message": "Data retrieved successfully",
            "data": item.model_dump()
        }, cls=DateTimeEncoder) + "\n"

@app.get("/search", response_model=ApiResponse)
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    try:
        items = [item async for item in search(query, _type)]
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
            data={"items": [item.model_dump() for item in items]}
        )
    
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Search failed: {str(e)}",
            data=None
        )

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

@app.get("/search", response_model=ApiResponse)
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    items = [item async for item in search(query, _type)]
    return ApiResponse(
        success=True,
        message="Data retrieved successfully",
        data={"items": [item.model_dump() for item in items]}
    )

async def process_scraping_task(task_id: str, query: str, _type: str) -> None:
    Task.save(task_id, "processing")
    items = [item async for item in search(query, _type)]
    serialized_items = json.dumps([item.model_dump() for item in items], cls=DateTimeEncoder)
    Task.save(task_id, "completed", serialized_items)

@app.get("/queue", response_model=ApiResponse)
async def queue_scraping(query: str, _type: Literal["profile", "company"] = "profile", background_tasks: BackgroundTasks = None):
    task_id = str(uuid.uuid4())
    Task.save(task_id, "queued")
    background_tasks.add_task(process_scraping_task, task_id, query, _type)
    return ApiResponse(
        success=True,
        message="Task queued successfully",
        data={"task_id": task_id}
    )

@app.get("/tasks", response_model=ApiResponse)
async def get_tasks():
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
    return ApiResponse(
        success=True,
        message="Tasks retrieved successfully",
        data={"tasks": tasks}
    )