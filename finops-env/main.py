from fastapi import FastAPI, HTTPException

from env.engine import FinOpsEngine
from env.models import Action, Observation
from env.tasks import get_task_score as compute_task_score, list_tasks

# 1. Initialize the FastAPI app and our Simulation Engine
app = FastAPI(title="OpenEnv FinOps Optimizer")
env = FinOpsEngine()

@app.get("/")
async def root():
    """Health check and basic info."""
    return {"message": "FinOps Cloud Optimizer OpenEnv is running."}

@app.post("/reset")
async def reset():
    """
    Standard OpenEnv API: Resets the environment to the initial state.
    Returns: The initial Observation.
    """
    initial_obs = env.reset()
    return initial_obs

@app.post("/step")
async def step(action: Action):
    """
    Standard OpenEnv API: Takes an action and returns the result.
    Args: action (Action model defined in models.py)
    Returns: {observation, reward, done, info}
    """
    try:
        obs, reward, done, info = env.step(action)
        return {
            "observation": obs,
            "reward": reward,
            "done": done,
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
async def state():
    """
    Standard OpenEnv API: Returns the current state without taking a step.
    """
    return env.get_observation("Current state requested.")

# --- Task Graders (For the OpenEnv Validator) ---


@app.get("/tasks")
async def tasks():
    """Lists available benchmark tasks."""
    return {"tasks": list_tasks()}

@app.get("/tasks/{task_id}/score")
async def get_task_score(task_id: str):
    """
    Programmatic graders to evaluate agent performance (0.0 to 1.0).
    """
    try:
        score = compute_task_score(env, task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "score": score}