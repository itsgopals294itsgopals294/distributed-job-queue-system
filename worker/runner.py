import asyncio
import traceback
import time
from typing import Dict, Any, Tuple
from tasks import TaskRegistry


class TaskRunner:
    @staticmethod
    async def run(
        job_type: str,
        payload: Dict[str, Any],
        timeout_seconds: int = 120
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], str, float]:
        """
        Executes a job task with timeout protection.
        Returns:
            (success, result_dict, error_message, logs, duration_ms)
        """
        start_time = time.time()
        logs_buffer = [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Task '{job_type}' execution started."]
        
        try:
            task_coro = TaskRegistry.execute(job_type, payload)
            result_dict, task_logs = await asyncio.wait_for(task_coro, timeout=timeout_seconds)
            
            if task_logs:
                logs_buffer.append(task_logs)
                
            duration_ms = (time.time() - start_time) * 1000
            logs_buffer.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Task '{job_type}' completed successfully in {duration_ms:.2f}ms.")
            return True, result_dict, None, "\n".join(logs_buffer), duration_ms

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            err_msg = f"TaskExecutionTimeout: Job exceeded execution timeout of {timeout_seconds} seconds."
            logs_buffer.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {err_msg}")
            return False, None, err_msg, "\n".join(logs_buffer), duration_ms

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            err_msg = f"{type(e).__name__}: {str(e)}"
            stack_trace = traceback.format_exc()
            logs_buffer.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {err_msg}\n{stack_trace}")
            return False, None, err_msg, "\n".join(logs_buffer), duration_ms
