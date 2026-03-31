============|

Z-Engine

============|

AI-Driven System Optimization · Built by Dipanjan Dutta, Age 16

============|

The Builder

============|

I'm a 16-year-old self-taught developer from Bankura, West Bengal, India.
No coaching. No smartphone. Just YouTube, curiosity, and a PC that kept
struggling under its own weight.

One day I watched my system sit at 7.7GB RAM usage with a single Chrome
tab open. Every optimization tool I tried applied the same generic fixes
regardless of what was actually happening. That frustrated me. So I built
something better.

Z-Engine is that something.

============|

Problem

============|

Modern operating systems produce extensive telemetry including CPU load,
memory pressure, storage utilization, and process activity. However, most
optimization tools rely on predefined tuning rules that do not account for
real system conditions.

These static approaches often apply generic optimizations that may be
ineffective or potentially harmful depending on system state.

=============|

Solution

=============|

Z-Engine introduces an AI-driven optimization pipeline that analyzes system
health, generates optimization strategies, critiques its own reasoning, and
produces controlled automation scripts.

The engine uses system telemetry to determine targeted improvements rather
than relying on rule-based tuning.

This creates a closed-loop architecture combining analysis, reasoning,
validation, and controlled execution.

====================|

Key Capabilities

====================|

AI-Based System Analysis
Evaluates system telemetry and produces stability and performance metrics.

Strategic Optimization Planning
Generates categorized improvements across memory, CPU scheduling, disk
performance, and background services.

Self-Critiquing AI Architecture
Uses iterative reasoning passes to evaluate and refine optimization
strategies — the AI checks its own work before acting.

Risk-Aware Execution Model
Each optimization task includes a stability risk profile before execution.

Script-Based Automation
Optimization plans are converted into executable PowerShell scripts for
transparent system modification.

Interactive Dashboard
A PySide6 interface visualizes system metrics, AI reasoning output, and
optimization plans in real time.

===================|

Real World Result

===================|

Tested on an Intel i3-7020U running Windows 11 23H2:

Before Z-Engine: 7.7GB / 8GB RAM used (1 Chrome tab + Task Manager)
After Z-Engine:  3.4GB RAM at idle

4.3GB freed. Autonomously. No manual intervention.

===================|

System Workflow

===================|

1. System Scan      – Collects real-time telemetry
2. AI Analysis      – ASI-1 evaluates stability and bottlenecks
3. Strategic Insight – Identifies optimization domains
4. Plan Generation  – Produces structured optimization tasks
5. Self-Critique    – AI reviews its own strategy for risks
6. Risk Evaluation  – Refines plan with stability profiles
7. Script Generation – Converts strategy to PowerShell script
8. Controlled Execution – User reviews, exports, or runs with admin confirm

=====================|

Design Principles

=====================|

- Telemetry-driven decision making
- Multi-pass AI reasoning
- Transparent and auditable automation
- Risk-aware system modification

====================|

Technology Stack

====================|

Python · PySide6 · psutil · ASI-1 API · PowerShell scripting

======================|

Running the Project

======================|

git clone https://github.com/Xpheonix0/Z-Engine
cd Z-Engine
pip install -r requirements.txt

--- Windows ---
set ASI_API_KEY=your-api-key-here
python main.py

Get your ASI-1 API key at: https://asi1.ai

===========================|

Agentic AI Architecture

===========================|

Z-Engine implements an agentic reasoning loop where the AI does not simply
generate answers but performs structured decision-making. The system
analyzes environment state, generates strategies, critiques its own
reasoning, and refines the resulting plan before execution.

This multi-pass architecture demonstrates how AI can function as an
autonomous decision system — not a chatbot, but an engine.

========================|

Traction & Recognition

========================|

· Podium finish at IIT Bombay Techfest competing against university students
· Submitted to 10+ international hackathons
· Live demo validated on real consumer hardware

          ||  Dipanjan Dutta, 16, India ||
