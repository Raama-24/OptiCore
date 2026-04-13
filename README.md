============|

Z-Engine

============|

AI-Driven System Optimization 

============|


Like many students, I often faced laptop performance issues such as slowdowns, lag during multitasking, and inconsistent system behavior. Existing tools either provided too much raw data or required manual technical intervention. This motivated me to build a solution that not only identifies performance problems but also resolves them intelligently and safely.

============|

Problem

============|

Modern computer systems often suffer from performance issues such as slowdowns, high memory usage, and inefficient background processes. 
Existing tools either provide complex raw data without actionable guidance or require manual technical intervention, making them inaccessible to non-expert users. Additionally, executing system-level optimizations can be risky, as incorrect commands may harm system stability or security.

As a result, users are left with underperforming systems, wasted resources, and no safe, automated way to optimize performance.

=============|

Solution

=============|

OptiCore scans and monitors system resources including CPU, memory, disk, and active processes in real time.
It evaluates system health and generates performance, stability, and efficiency scores.
The system identifies bottlenecks and provides targeted optimization insights.
It creates structured optimization plans and converts them into executable scripts.
Safety mechanisms such as risk classification, validation, and user confirmation ensure secure execution.
Backup and restore features allow users to safely revert changes if needed.

====================|

Key Capabilities

====================|

AI-Based System Analysis
Evaluates system telemetry and generates stability and performance metrics.

Strategic Optimization Planning
Creates categorized improvements across memory, CPU scheduling, disk performance, and background services.

Self-Critiquing AI Architecture
Uses iterative reasoning to evaluate and refine optimization strategies before execution.

Risk-Aware Execution Model
Assigns a stability risk profile to each optimization task prior to execution.

Script-Based Automation
Converts optimization plans into executable PowerShell scripts for transparent system modification.

Interactive Dashboard
Provides a PySide6 interface to visualize system metrics, analysis output, and optimization plans in real time.

===================|

Real World Result

===================|

Before OptiCore: 6.8GB / 16GB RAM used (multiple Chrome tabs + background apps)
After OptiCore: 3.9GB RAM at idle

~2.9GB memory freed through optimization of background services, startup processes, and memory usage.
System responsiveness improved with faster app switching and reduced idle load.

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

-All optimizations are based on real-time system data, not assumptions
-Optimization strategies are evaluated and refined through iterative analysis
-Every action is script-based, logged, and visible to the user

====================|

Technology Stack

====================|

Python · PySide6 · psutil · ASI-1 API · PowerShell scripting

======================|

Running the Project

======================|

git clone https://github.com/Raama-24/OptiCore.git
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
