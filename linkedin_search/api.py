from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
import uuid
import json
from linkedin_search.linkedin import LinkedIn, LinkedInProfile, LinkedInCompany
from linkedin_search.tasks import Task
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Literal, Union

app = FastAPI()

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def get_search_history(query: str, _type: str) -> List[Union[LinkedInProfile, LinkedInCompany]]:
    history = await Task.get_search_history(f"{query}_{_type}")
    if history:
        return [LinkedInProfile(**profile) if _type == "profile" else LinkedInCompany(**profile) for profile in json.loads(history)]
    return None

async def save_search_history(query: str, items: List[Union[LinkedInProfile, LinkedInCompany]], _type: str):
    serialized_items = json.dumps([item.model_dump() for item in items], cls=DateTimeEncoder)
    await Task.save_search_history(f"{query}_{_type}", serialized_items)

async def search(query: str, _type: str = "profile") -> AsyncGenerator[Union[LinkedInProfile, LinkedInCompany], None]:
    history_items = await get_search_history(query, _type)
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
        await save_search_history(query, items, _type)

async def create_streaming_response(query: str, _type: Literal["profile", "company"]="profile") -> AsyncGenerator[str, None]:
    async for item in search(query, _type):
        yield json.dumps(item.model_dump(), cls=DateTimeEncoder) + "\n"

@app.get("/stream", response_class=StreamingResponse)
async def get_profile_stream(query: str, _type: Literal["profile", "company"] = "profile"):
    return StreamingResponse(create_streaming_response(query, _type), media_type="text/event-stream")

@app.get("/search")
async def search_data(query: str, _type: Literal["profile", "company"] = "profile"):
    return [item async for item in search(query, _type)]

async def process_scraping_task(task_id: str, query: str, _type: str) -> None:
    await Task.save(task_id, "processing")
    items = [item async for item in search(query, _type)]
    serialized_items = json.dumps([item.model_dump() for item in items], cls=DateTimeEncoder)
    await Task.save(task_id, "completed", serialized_items)

async def format_task_output(task: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    output = json.loads(task.get('output')) if task.get('output') else None
    return {
        "task_id": task_id,
        "status": task.get('status'),
        "output": output
    }

@app.get("/queue")
async def queue_scraping(query: str, _type: Literal["profile", "company"] = "profile", background_tasks: BackgroundTasks = None):
    task_id = str(uuid.uuid4())
    await Task.save(task_id, "queued")
    background_tasks.add_task(process_scraping_task, task_id, query, _type)
    return {"task_id": task_id}

@app.get("/tasks")
async def get_tasks():
    task_keys = await Task.get_all_keys()
    tasks = []
    for task_id in task_keys:
        task = await Task.get(task_id)
        if task:
            tasks.append(await format_task_output(task, task_id))
    return tasks