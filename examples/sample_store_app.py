"""
Nexus Sample Store - Real-World Application Integration Demo
Demonstrates how an external customer-facing web app (e.g., E-Commerce Storefront)
connects to the Nexus Distributed Job Queue to offload heavy background tasks.

Runs on: http://127.0.0.1:5000
"""

import sys
import time
import uuid
import random
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path so we can import the official Python SDK
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sdk.python.jobqueue import JobQueue

# Initialize the queue SDK connecting to local backend on 8000
queue = JobQueue(
    base_url="http://127.0.0.1:8000",
    api_key="jq_live_enterprise_secret_key"
)

app = FastAPI(
    title="Nexus Gear Storefront (Sample External App)",
    description="Sample web store demonstrating non-blocking background task delegation."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderRequest(BaseModel):
    product_name: str
    price: float
    customer_email: str
    simulate_failure: bool = False


STORE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus Gear Store - Live External App Integration Demo</title>
  <style>
    :root {
      --bg: #090B10;
      --card-bg: #11141D;
      --card-border: #1E2333;
      --primary: #3B82F6;
      --primary-hover: #2563EB;
      --success: #10B981;
      --warning: #F59E0B;
      --danger: #EF4444;
      --text: #F3F4F6;
      --text-muted: #9CA3AF;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding-bottom: 80px;
    }

    /* Top banner linking to Job Queue Matrix */
    .integration-banner {
      background: linear-gradient(90deg, #1E1B4B 0%, #172554 100%);
      border-bottom: 1px solid #3730A3;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 13px;
    }
    .banner-left { display: flex; align-items: center; gap: 10px; }
    .badge-live {
      background: #10B981;
      color: #042F2E;
      font-weight: 700;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .banner-link {
      background: #3B82F6;
      color: #FFFFFF;
      text-decoration: none;
      padding: 6px 14px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .banner-link:hover { background: #2563EB; transform: translateY(-1px); }

    .header {
      max-width: 1240px;
      margin: 28px auto 20px;
      padding: 0 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 16px;
    }
    .brand h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; }
    .brand p { color: var(--text-muted); font-size: 14px; margin-top: 4px; }

    /* User Profile Bar */
    .profile-bar {
      background: #11141D;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
    }
    .profile-input {
      background: #090B10;
      border: 1px solid #232E47;
      color: #FFF;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: var(--font-mono);
      width: 220px;
    }

    .container {
      max-width: 1240px;
      margin: 0 auto;
      padding: 0 24px;
      display: grid;
      grid-template-columns: 1fr 390px;
      gap: 32px;
    }
    @media (max-width: 960px) {
      .container { grid-template-columns: 1fr; }
    }

    /* Product Grid */
    .section-title {
      font-size: 15px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .products-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
      gap: 20px;
      margin-bottom: 28px;
    }
    .product-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: border-color 0.2s, transform 0.2s;
    }
    .product-card:hover {
      border-color: #374151;
      transform: translateY(-2px);
    }
    .product-icon {
      font-size: 36px;
      margin-bottom: 12px;
      display: inline-block;
    }
    .product-tag {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      color: #60A5FA;
      background: #1E293B;
      padding: 2px 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      align-self: flex-start;
    }
    .product-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
    .product-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; min-height: 40px; }
    .product-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--card-border);
      padding-top: 14px;
      margin-top: 8px;
    }
    .product-price { font-size: 20px; font-weight: 800; color: #FFFFFF; }

    .btn {
      background: var(--primary);
      color: #FFFFFF;
      border: none;
      border-radius: 8px;
      padding: 10px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease-in-out;
    }
    .btn:hover { background: var(--primary-hover); }
    .btn:active { transform: scale(0.98); }
    .btn-secondary {
      background: #1F2937;
      color: var(--text);
      border: 1px solid #374151;
    }
    .btn-secondary:hover { background: #374151; }
    .btn-danger {
      background: #7F1D1D;
      color: #FCA5A5;
      border: 1px solid #991B1B;
    }
    .btn-danger:hover { background: #991B1B; color: #FFF; }

    /* Simulation Control Box */
    .sim-panel {
      background: #11141D;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .sim-buttons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    /* Right Sidebar - Realtime Order Receipt & Telemetry */
    .sidebar { display: flex; flex-direction: column; gap: 20px; }
    .receipt-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
    }
    .receipt-card.active-order {
      border-color: #2563EB;
      box-shadow: 0 0 25px rgba(37, 99, 235, 0.25);
    }
    .perf-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #064E3B;
      color: #6EE7B7;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      font-family: var(--font-mono);
      margin-top: 8px;
    }

    /* Step Timeline */
    .timeline {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      position: relative;
    }
    .step {
      display: flex;
      gap: 12px;
      font-size: 12px;
    }
    .step-dot {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #1E2333;
      border: 2px solid #374151;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      font-weight: 700;
      flex-shrink: 0;
    }
    .step.done .step-dot {
      background: var(--success);
      border-color: var(--success);
      color: #042F2E;
    }
    .step.active .step-dot {
      background: var(--primary);
      border-color: #60A5FA;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.6);
    }
    .step.failed .step-dot {
      background: var(--danger);
      border-color: var(--danger);
      color: #FFF;
    }
    .step-content { flex: 1; }
    .step-title { font-weight: 600; color: #FFFFFF; }
    .step-desc { color: var(--text-muted); font-size: 11px; margin-top: 2px; }

    /* Code Snippet Drawer */
    .code-box {
      background: #080A0F;
      border: 1px solid #1E2333;
      border-radius: 8px;
      padding: 14px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: #E2E8F0;
      overflow-x: auto;
      line-height: 1.6;
    }
    .code-comment { color: #64748B; }
    .code-kw { color: #F472B6; }
    .code-str { color: #34D399; }
    .code-fn { color: #60A5FA; }

    /* Order History Table */
    .orders-table-wrapper {
      background: #11141D;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-top: 32px;
    }
    .orders-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 12px;
    }
    .orders-table th {
      text-align: left;
      padding: 10px 12px;
      color: var(--text-muted);
      border-bottom: 1px solid #1E2333;
      font-size: 11px;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }
    .orders-table td {
      padding: 12px;
      border-bottom: 1px solid #1A1F2C;
      font-family: var(--font-mono);
    }
    .orders-table tr:hover { background: #161A26; }

    /* Status Badges */
    .badge-status {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
    }
    .badge-completed { background: #064E3B; color: #6EE7B7; }
    .badge-running { background: #1E3A8A; color: #93C5FD; }
    .badge-queued { background: #78350F; color: #FDE68A; }
    .badge-dlq { background: #7F1D1D; color: #FCA5A5; }

    /* Live Feed */
    .feed-list {
      max-height: 200px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .feed-item {
      background: #0B0E14;
      border: 1px solid #1A1F2C;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-family: var(--font-mono);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  </style>
</head>
<body>

  <!-- Top Real-Life Integration Banner -->
  <div class="integration-banner">
    <div class="banner-left">
      <span class="badge-live">● Sample Web App</span>
      <span><strong>Nexus Gear Storefront</strong> is running on port <strong>5000</strong> and offloading tasks to <strong>Nexus Queue (Port 8000)</strong>!</span>
    </div>
    <div>
      <a href="http://127.0.0.1:8000/" target="_blank" class="banner-link">
        <span>Open Job Queue Console in Split View ↗</span>
      </a>
    </div>
  </div>

  <div class="header">
    <div class="brand">
      <h1>Nexus Premium Storefront</h1>
      <p>Simulating real-world user checkouts with asynchronous task offloading via <code>sdk/python/jobqueue.py</code></p>
    </div>

    <div class="profile-bar">
      <span>Customer:</span>
      <input id="customerEmail" type="email" value="alex.mercer@startup.io" class="profile-input" placeholder="Your test email" />
    </div>
  </div>

  <div class="container">
    <!-- Left Column: Products & Trigger Scenarios -->
    <div>
      <div class="section-title">🛒 Featured Products (Click "1-Click Buy" to test checkout)</div>
      
      <div class="products-grid">
        <!-- Product 1 -->
        <div class="product-card">
          <div>
            <span class="product-icon">🎧</span>
            <div><span class="product-tag">Bestseller</span></div>
            <div class="product-title">Aura Pro Wireless Headphones</div>
            <div class="product-desc">Studio audio with adaptive ANC, spatial audio, and 40h battery.</div>
          </div>
          <div class="product-footer">
            <div class="product-price">$349</div>
            <button class="btn" onclick="placeOrder('Aura Pro Headphones', 349.00)">
              ⚡ 1-Click Buy
            </button>
          </div>
        </div>

        <!-- Product 2 -->
        <div class="product-card">
          <div>
            <span class="product-icon">⌨️</span>
            <div><span class="product-tag">Hot Item</span></div>
            <div class="product-title">Apex Q1 Pro Mechanical Keyboard</div>
            <div class="product-desc">Full CNC aluminum chassis, hot-swappable switches, wireless.</div>
          </div>
          <div class="product-footer">
            <div class="product-price">$189</div>
            <button class="btn" onclick="placeOrder('Apex Q1 Pro Keyboard', 189.00)">
              ⚡ 1-Click Buy
            </button>
          </div>
        </div>

        <!-- Product 3 -->
        <div class="product-card">
          <div>
            <span class="product-icon">🖥️</span>
            <div><span class="product-tag">Pre-Order</span></div>
            <div class="product-title">Studio Display 4K Ultra</div>
            <div class="product-desc">27-inch 5K Retina resolution with built-in 12MP center camera.</div>
          </div>
          <div class="product-footer">
            <div class="product-price">$1,199</div>
            <button class="btn" onclick="placeOrder('Studio Display 4K', 1199.00)">
              ⚡ 1-Click Buy
            </button>
          </div>
        </div>

        <!-- Product 4 -->
        <div class="product-card">
          <div>
            <span class="product-icon">🚀</span>
            <div><span class="product-tag">Enterprise</span></div>
            <div class="product-title">Nexus Edge Compute Blade</div>
            <div class="product-desc">128-core ARM compute node with PCIe 5.0 and dual 100GbE NICs.</div>
          </div>
          <div class="product-footer">
            <div class="product-price">$2,499</div>
            <button class="btn" onclick="placeOrder('Nexus Edge Blade', 2499.00)">
              ⚡ 1-Click Buy
            </button>
          </div>
        </div>
      </div>

      <!-- Real World Scenarios Panel -->
      <div class="sim-panel">
        <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">⚡ Real-World Traffic & Chaos Simulators</div>
        <div style="color: var(--text-muted); font-size: 12px;">Test how your Job Queue handles traffic surges and flaky external vendors.</div>
        
        <div class="sim-buttons">
          <button class="btn btn-secondary" onclick="simulateFlashSale()">
            <span>💥 Flash Sale (5 Orders at Once)</span>
          </button>
          <button class="btn btn-secondary" onclick="simulateBulkExport()">
            <span>📊 Bulk Accounting Ledger Export</span>
          </button>
          <button class="btn btn-danger" onclick="simulateChaosOrder()">
            <span>⚠️ Test Flaky Mail Server (DLQ Quarantine)</span>
          </button>
        </div>
      </div>

      <!-- Live Order History Ledger -->
      <div class="orders-table-wrapper">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 700; font-size: 14px;">📋 Recent Session Orders Ledger</div>
          <span style="font-size: 11px; color: var(--text-muted);">Auto-synchronizing with Queue</span>
        </div>

        <div style="overflow-x: auto;">
          <table class="orders-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Product</th>
                <th>Customer</th>
                <th>Store Speed</th>
                <th>Queue Task ID</th>
                <th>Task Status</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="ordersTableBody">
              <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">
                  No orders placed yet. Click <strong>"⚡ 1-Click Buy"</strong> above to see instant order delegation!
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- How It Connects Code Box -->
      <div class="section-title" style="margin-top: 32px;">🔌 How This App Connects In Real Life (Python SDK)</div>
      <div class="code-box">
<span class="code-comment"># In your real application (Django, Flask, FastAPI, or script):</span>
<span class="code-kw">from</span> sdk.python.jobqueue <span class="code-kw">import</span> JobQueue

queue = JobQueue(base_url=<span class="code-str">"http://127.0.0.1:8000"</span>)

<span class="code-comment"># Dispatches instantly in ~20 milliseconds! Web user never gets frozen waiting for emails or PDFs:</span>
job = queue.<span class="code-fn">dispatch</span>(
    job_type=<span class="code-str">"email_dispatch"</span>,
    priority=<span class="code-str">"high"</span>,
    payload={<span class="code-str">"to"</span>: customer_email, <span class="code-str">"order_id"</span>: order_id}
)
      </div>
    </div>

    <!-- Right Column: Live Receipt & Job Queue Sync -->
    <div class="sidebar">
      
      <!-- Active Order Receipt -->
      <div id="receiptBox" class="receipt-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; font-size: 14px;">🛍️ Latest Checkout Receipt</span>
          <span id="orderBadge" style="font-size: 11px; color: var(--text-muted);">Ready</span>
        </div>

        <div id="orderEmptyState" style="padding: 28px 0; text-align: center; color: var(--text-muted); font-size: 13px;">
          Click <strong>"⚡ 1-Click Buy"</strong> on any product to see the instant checkout speed and background queue handoff.
        </div>

        <div id="orderDetails" style="display: none; margin-top: 14px;">
          <div style="font-size: 18px; font-weight: 800; color: #FFF;" id="orderProductName">-</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
            Order ID: <span id="orderIdText" style="font-family: var(--font-mono); color: #60A5FA;">-</span>
          </div>

          <div class="perf-badge">
            ⚡ Checkout Response: <span id="latencyText">24ms</span>
          </div>

          <p style="font-size: 11px; color: #9CA3AF; margin-top: 10px; line-height: 1.4;">
            The store confirmed the customer in <strong id="latencyHighlight">24ms</strong>! 
            Slow tasks (sending receipt email, updating accounting) were pushed to the queue.
          </p>

          <!-- Timeline -->
          <div class="timeline" id="timelineBox">
            <div class="step done" id="step1">
              <div class="step-dot">✓</div>
              <div class="step-content">
                <div class="step-title">1. Checkout Confirmed</div>
                <div class="step-desc">Order saved in 24ms; customer relieved</div>
              </div>
            </div>

            <div class="step active" id="step2">
              <div class="step-dot">2</div>
              <div class="step-content">
                <div class="step-title">2. Pushed to Nexus Queue</div>
                <div class="step-desc" id="step2Desc">Job dispatched to Priority Queue</div>
              </div>
            </div>

            <div class="step" id="step3">
              <div class="step-dot">3</div>
              <div class="step-content">
                <div class="step-title">3. Worker Processing</div>
                <div class="step-desc" id="step3Desc">Worker node running email & exports</div>
              </div>
            </div>

            <div class="step" id="step4">
              <div class="step-dot">4</div>
              <div class="step-content">
                <div class="step-title">4. Finished</div>
                <div class="step-desc" id="step4Desc">Receipt emailed, ERP synced</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Stream Feed -->
      <div class="receipt-card">
        <div style="font-weight: 700; font-size: 13px; margin-bottom: 12px;">📊 Live Store Activity Feed</div>
        <div class="feed-list" id="feedList">
          <div class="feed-item">
            <span>Store initialized on port 5000</span>
            <span style="color: #10B981;">ONLINE</span>
          </div>
        </div>
      </div>

    </div>
  </div>

  <script>
    const FEED_LIST = document.getElementById("feedList");
    const sessionOrders = [];

    function addFeed(text, tag = "INFO", tagColor = "#60A5FA") {
      const div = document.createElement("div");
      div.className = "feed-item";
      div.innerHTML = `<span>${text}</span><span style="color: ${tagColor}; font-weight: 600;">${tag}</span>`;
      FEED_LIST.prepend(div);
    }

    async function placeOrder(productName, price, simulateFailure = false) {
      const receipt = document.getElementById("receiptBox");
      const empty = document.getElementById("orderEmptyState");
      const details = document.getElementById("orderDetails");
      const email = document.getElementById("customerEmail").value.trim() || "buyer@customer.com";

      receipt.classList.add("active-order");
      empty.style.display = "none";
      details.style.display = "block";
      receipt.scrollIntoView({ behavior: 'smooth', block: 'center' });

      document.getElementById("orderProductName").innerText = productName + (simulateFailure ? " (Fail Test)" : "");
      document.getElementById("orderBadge").innerText = "Processing...";
      document.getElementById("orderBadge").style.color = "#F59E0B";

      // Reset steps
      setStep("step2", "active", "2", "Dispatching to Nexus Queue...");
      setStep("step3", "waiting", "3", "Worker waiting");
      setStep("step4", "waiting", "4", "Awaiting execution");

      const t0 = performance.now();
      try {
        const res = await fetch("/api/checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_name: productName,
            price: price,
            customer_email: email,
            simulate_failure: simulateFailure
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.error || `Server HTTP ${res.status}`);
        }

        const data = await res.json();
        const latency = Math.round(performance.now() - t0);

        document.getElementById("orderIdText").innerText = data.order_id;
        document.getElementById("latencyText").innerText = `${latency}ms`;
        document.getElementById("latencyHighlight").innerText = `${latency}ms`;

        addFeed(`Order ${data.order_id} confirmed in ${latency}ms`, "ORDER", "#10B981");

        const primaryJob = (data.jobs && data.jobs.length > 0) ? data.jobs[0] : null;
        const jobId = primaryJob ? primaryJob.id : "job_" + Math.random().toString(36).substring(2, 8);

        setStep("step2", "done", "✓", `Queued Job #${jobId.substring(0, 8)}`);
        setStep("step3", "active", "3", "Worker node leased task...");

        // Record in session ledger table
        const orderRecord = {
          order_id: data.order_id,
          product: productName,
          email: email,
          latency: latency,
          job_id: jobId,
          status: "QUEUED"
        };
        sessionOrders.unshift(orderRecord);
        renderOrdersTable();

        // Poll job status until done
        trackJob(jobId, orderRecord);

      } catch (err) {
        console.error(err);
        setStep("step2", "failed", "✕", `Error: ${err.message}`);
        document.getElementById("orderBadge").innerText = "Failed";
        document.getElementById("orderBadge").style.color = "#EF4444";
        addFeed(`Checkout error: ${err.message}`, "ERR", "#EF4444");
      }
    }

    function setStep(id, state, num, desc) {
      const el = document.getElementById(id);
      el.className = `step ${state}`;
      el.querySelector(".step-dot").innerText = num;
      if (desc) el.querySelector(".step-desc").innerText = desc;
    }

    async function trackJob(jobId, orderRecord) {
      let attempts = 0;
      let errorCount = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch(`/api/job-status/${jobId}`);
          if (!res.ok) {
            errorCount++;
            if (errorCount > 8) clearInterval(poll);
            return;
          }
          const job = await res.json();
          errorCount = 0;

          if (job.status === "COMPLETED") {
            clearInterval(poll);
            setStep("step2", "done", "✓", "Dispatched to Nexus Queue");
            setStep("step3", "done", "✓", "Worker executed email task");
            setStep("step4", "done", "✓", "Email delivered & synced");
            document.getElementById("orderBadge").innerText = "Completed";
            document.getElementById("orderBadge").style.color = "#10B981";
            orderRecord.status = "COMPLETED";
            renderOrdersTable();
            addFeed(`Job #${jobId.substring(0, 8)} finished with status COMPLETED`, "SUCCESS", "#10B981");
          } else if (job.status === "DEAD_LETTER") {
            clearInterval(poll);
            setStep("step2", "done", "✓", "Dispatched to Nexus Queue");
            setStep("step3", "failed", "✕", `Retries exhausted (${job.retry_count || 1} retries)`);
            setStep("step4", "failed", "DLQ", "Safely quarantined to DLQ!");
            document.getElementById("orderBadge").innerText = "Moved to DLQ";
            document.getElementById("orderBadge").style.color = "#EF4444";
            orderRecord.status = "DEAD_LETTER";
            renderOrdersTable();
            addFeed(`Job #${jobId.substring(0, 8)} quarantined into Dead-Letter Queue`, "DLQ", "#EF4444");
          } else if (job.status === "RUNNING") {
            setStep("step2", "done", "✓", "Dispatched to Nexus Queue");
            setStep("step3", "active", "3", "Worker node leased task...");
            orderRecord.status = "RUNNING";
            renderOrdersTable();
          } else if (attempts > 60) {
            clearInterval(poll);
          }
        } catch (e) {
          errorCount++;
          if (errorCount > 8) clearInterval(poll);
        }
      }, 600);
    }

    function renderOrdersTable() {
      const tbody = document.getElementById("ordersTableBody");
      if (!tbody) return;
      if (sessionOrders.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">No orders placed yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = sessionOrders.map(o => {
        const badgeClass = o.status === 'COMPLETED' ? 'badge-completed' 
          : o.status === 'RUNNING' ? 'badge-running' 
          : o.status === 'DEAD_LETTER' ? 'badge-dlq' : 'badge-queued';

        return `
          <tr>
            <td style="font-weight: 700; color: #FFF;">${o.order_id}</td>
            <td style="color: #E2E8F0;">${o.product}</td>
            <td style="color: var(--text-muted);">${o.email}</td>
            <td style="color: #6EE7B7; font-weight: 700;">${o.latency}ms</td>
            <td style="color: #60A5FA;">${o.job_id.substring(0, 8)}</td>
            <td><span class="badge-status ${badgeClass}">${o.status}</span></td>
            <td style="text-align: right;">
              <a href="http://127.0.0.1:8000/" target="_blank" style="color: #3B82F6; text-decoration: none; font-size: 11px;">
                Inspect in Queue ↗
              </a>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function simulateFlashSale() {
      addFeed("⚡ Flash Sale triggered! Sending 5 burst orders simultaneously...", "BURST", "#F59E0B");
      try {
        const res = await fetch("/api/flash-sale", { method: "POST" });
        const data = await res.json();
        addFeed(`5 orders dispatched (Total ${data.total_jobs} background jobs queued) in ${data.total_time_ms}ms!`, "SAVED", "#10B981");
        placeOrder("Flash Sale Bundle", 499.00);
      } catch (e) {
        console.error(e);
      }
    }

    async function simulateBulkExport() {
      addFeed("📊 Dispatching bulk accounting ledger export (10,000 records)...", "EXPORT", "#3B82F6");
      try {
        const res = await fetch("/api/bulk-export", { method: "POST" });
        const data = await res.json();
        addFeed(`Data export job queued: #${data.job.id.substring(0, 8)}`, "QUEUED", "#10B981");
      } catch (e) {
        console.error(e);
      }
    }

    function simulateChaosOrder() {
      addFeed("🧪 Simulating order with failing SMTP server (Simulate DLQ Quarantining)", "CHAOS", "#EF4444");
      placeOrder("Chaos Flaky Item", 99.00, true);
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def serve_store_frontend():
    """Serves the interactive E-Commerce Storefront."""
    return HTMLResponse(content=STORE_HTML)


@app.post("/api/checkout")
async def checkout(order: OrderRequest):
    """
    Simulates a fast customer checkout.
    Dispatches 2 background tasks to the Nexus Distributed Job Queue:
    1. 'email_dispatch' (P0 High priority)
    2. 'data_export' (P2 Low priority - transaction ledger)
    """
    order_id = f"ORD-{random.randint(1000, 9999)}"
    t_start = time.perf_counter()

    # 1. Dispatch Email Task (High Priority)
    email_job = await asyncio.to_thread(
        queue.dispatch,
        job_type="email_dispatch",
        priority="high",
        payload={
            "to": order.customer_email,
            "subject": f"Order Confirmation {order_id} - {order.product_name}",
            "order_id": order_id,
            "simulate_fail": order.simulate_failure
        },
        max_retries=2 if order.simulate_failure else 3
    )

    # 2. Dispatch Accounting Ledger Export (Low Priority)
    ledger_job = await asyncio.to_thread(
        queue.dispatch,
        job_type="data_export",
        priority="low",
        payload={
            "format": "csv",
            "record_count": 1,
            "order_id": order_id
        }
    )

    latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "success": True,
        "order_id": order_id,
        "dispatch_latency_ms": latency_ms,
        "jobs": [email_job, ledger_job]
    }


@app.post("/api/flash-sale")
async def flash_sale_burst():
    """Simulates a sudden flash sale of 5 concurrent orders."""
    t_start = time.perf_counter()
    jobs_created = []

    for i in range(5):
        order_id = f"SALE-{random.randint(1000, 9999)}"
        email_job = await asyncio.to_thread(
            queue.dispatch,
            job_type="email_dispatch",
            priority="high",
            payload={
                "to": f"customer_{i+1}@flashsale.com",
                "subject": f"Flash Sale Confirmation {order_id}",
                "order_id": order_id
            }
        )
        jobs_created.append(email_job)

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "status": "burst_queued",
        "orders_created": 5,
        "total_jobs": len(jobs_created),
        "total_time_ms": elapsed_ms
    }


@app.post("/api/bulk-export")
async def bulk_export():
    """Dispatches a heavy background ETL data export."""
    job = await asyncio.to_thread(
        queue.dispatch,
        job_type="data_export",
        priority="low",
        payload={"format": "parquet", "record_count": 10000}
    )
    return {"status": "dispatched", "job": job}


@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Proxies status check to the Job Queue backend via SDK."""
    try:
        status = await asyncio.to_thread(queue.get_status, job_id)
        return status
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    print("Starting Nexus Sample Store App on http://127.0.0.1:5000...", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=5000)
