from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
import uuid
import json
from linkedin_search.linkedin import LinkedIn, LinkedInProfile
from linkedin_search.tasks import Task
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List

app = FastAPI()

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def get_search_history(query: str) -> List[LinkedInProfile]:
    history = await Task.get_search_history(query)
    if history:
        return [LinkedInProfile(**profile) for profile in json.loads(history)]
    return None

async def save_search_history(query: str, profiles: List[LinkedInProfile]):
    serialized_profiles = json.dumps([profile.model_dump() for profile in profiles], cls=DateTimeEncoder)
    await Task.save_search_history(query, serialized_profiles)

async def search(query: str) -> AsyncGenerator[LinkedInProfile, None]:
    history_profiles = await get_search_history(query)
    if history_profiles:
        for profile in history_profiles:
            yield profile
    else:
        linkedin = LinkedIn()
        profiles = []
        async for profile in linkedin.profile(query):
            profiles.append(profile)
            yield profile
        await save_search_history(query, profiles)

async def create_streaming_response(query: str) -> AsyncGenerator[str, None]:
    yield json.dumps({"status": "Scraping"}) + "\n"
    async for profile in search(query):
        yield json.dumps(profile.model_dump(), cls=DateTimeEncoder) + "\n"

@app.get("/stream", response_class=StreamingResponse, response_model=LinkedInProfile)
async def get_profile_stream(query: str):
    return StreamingResponse(create_streaming_response(query), media_type="text/event-stream")

@app.get("/search", response_model=List[LinkedInProfile])
async def get_profile(query: str):
    return [profile async for profile in search(query)]

async def process_scraping_task(task_id: str, query: str) -> None:
    await Task.save(task_id, "processing")
    profiles = [profile async for profile in search(query)]
    serialized_profiles = json.dumps([profile.model_dump() for profile in profiles], cls=DateTimeEncoder)
    await Task.save(task_id, "completed", serialized_profiles)

async def format_task_output(task: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    output = json.loads(task.get('output')) if task.get('output') else None
    return {
        "task_id": task_id,
        "status": task.get('status'),
        "output": output
    }

@app.get("/queue")
async def queue_scraping(query: str, background_tasks: BackgroundTasks = None):
    task_id = str(uuid.uuid4())
    await Task.save(task_id, "queued")
    background_tasks.add_task(process_scraping_task, task_id, query)
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