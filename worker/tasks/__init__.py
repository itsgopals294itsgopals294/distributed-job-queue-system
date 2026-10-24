import asyncio
import random
import time
from typing import Dict, Any, Tuple


class TaskRegistry:
    _handlers = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls._handlers[name] = func
            return func
        return decorator

    @classmethod
    async def execute(cls, job_type: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Executes registered handler for job_type.
        Returns: (result_dict, log_string)
        """
        handler = cls._handlers.get(job_type)
        if not handler:
            raise ValueError(f"Unknown job_type: '{job_type}'. Registered types: {list(cls._handlers.keys())}")
        return await handler(payload)


@TaskRegistry.register("email_dispatch")
async def handle_email_dispatch(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    to_email = payload.get("to", "recipient@example.com")
    subject = payload.get("subject", "Automated Notification")
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Preparing email template for {to_email}", f"Subject: {subject}"]
    await asyncio.sleep(0.5)
    
    if simulate_fail:
        logs.append("SMTP Server connection timed out! Refusing to send.")
        raise RuntimeError("SMTP Connection Error 504: Gateway Timeout")

    logs.append("DKIM signed and TLS handshake established.")
    logs.append(f"Email successfully delivered to {to_email}.")
    result = {
        "status": "delivered",
        "recipient": to_email,
        "message_id": f"msg_{int(time.time()*1000)}",
        "timestamp": time.time()
    }
    return result, "\n".join(logs)


@TaskRegistry.register("data_export")
async def handle_data_export(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    format_type = payload.get("format", "csv").lower()
    record_count = payload.get("record_count", 500)
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Starting data export in format '{format_type}' for {record_count} records."]
    await asyncio.sleep(0.8)
    
    if simulate_fail:
        logs.append("Disk space quota exceeded or export buffer overflow.")
        raise IOError("IOError: Disk buffer exceeded allocation quota")

    logs.append(f"Extracted {record_count} records from data warehouse.")
    logs.append(f"Compressed output into {format_type}.gz.")
    result = {
        "format": format_type,
        "exported_records": record_count,
        "file_size_bytes": record_count * 142,
        "download_url": f"https://exports.internal.io/files/export_{int(time.time())}.{format_type}"
    }
    return result, "\n".join(logs)


@TaskRegistry.register("image_resize")
async def handle_image_resize(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    image_url = payload.get("image_url", "https://assets.example.com/banner.jpg")
    targets = payload.get("dimensions", ["thumbnail_150x150", "medium_600x400", "large_1200x800"])
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Downloading original image from {image_url}..."]
    await asyncio.sleep(0.6)
    
    if simulate_fail:
        logs.append("Image decode error: corrupt JPEG header.")
        raise ValueError("ImageProcessingError: Invalid or corrupt JPEG header")

    generated = {}
    for d in targets:
        logs.append(f"Resized image variant generated: {d}")
        generated[d] = f"https://cdn.example.com/images/{d}_{int(time.time())}.webp"

    logs.append("Optimized color palette and generated WebP assets.")
    result = {
        "original_url": image_url,
        "variants": generated,
        "compression_ratio": "68%"
    }
    return result, "\n".join(logs)


@TaskRegistry.register("ml_inference")
async def handle_ml_inference(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    model_name = payload.get("model", "sentiment-v2")
    inputs = payload.get("inputs", ["Great product, arrived quickly!"])
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Loading model weights for '{model_name}'...", f"Batch size: {len(inputs)}"]
    await asyncio.sleep(1.0)
    
    if simulate_fail:
        logs.append("CUDA Out Of Memory error during forward pass.")
        raise MemoryError("CUDARuntimeError: Out of memory on GPU device 0")

    predictions = []
    for text in inputs:
        score = random.uniform(0.85, 0.99)
        predictions.append({"text": text, "label": "POSITIVE", "confidence": round(score, 4)})
        logs.append(f"Inference completed for: '{text[:30]}...' -> score: {score:.3f}")

    logs.append("Batch inference successfully completed.")
    result = {
        "model": model_name,
        "predictions": predictions,
        "latency_ms": 98.4
    }
    return result, "\n".join(logs)


@TaskRegistry.register("webhook_delivery")
async def handle_webhook_delivery(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    target_url = payload.get("url", "https://api.partner.com/events")
    event_type = payload.get("event", "payment.captured")
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Constructing webhook envelope for {event_type}", f"Dispatching to endpoint: {target_url}"]
    await asyncio.sleep(0.4)
    
    if simulate_fail:
        logs.append("Partner webhook returned HTTP 500 Internal Server Error.")
        raise ConnectionError("RemoteHostError: HTTP 500 Internal Server Error")

    logs.append("Webhook response received: HTTP 200 OK.")
    result = {
        "url": target_url,
        "event": event_type,
        "response_code": 200,
        "attempt_time": time.time()
    }
    return result, "\n".join(logs)


@TaskRegistry.register("custom_calc")
async def handle_custom_calc(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    n = payload.get("n", 25)
    simulate_fail = payload.get("simulate_fail", False)
    
    logs = [f"Computing Fibonacci sequence and primes up to N={n}..."]
    await asyncio.sleep(0.3)
    
    if simulate_fail:
        raise ArithmeticError("Arithmetic calculation overflow in matrix expansion")

    # Simple Fibonacci calculation
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b

    logs.append(f"Fibonacci({n}) evaluated to {a}.")
    result = {
        "n": n,
        "fibonacci_result": a,
        "timestamp": time.time()
    }
    return result, "\n".join(logs)
