# Project 2 — Phase 1: LangChain + LangGraph Learning Log

## Description
This folder contains a single styled HTML page that showcases what I learned this week about LangChain and LangGraph — chains, prompt templates, output parsers, memory, tool-calling, LangGraph's node/edge/state model, and orchestrator agents.

## How to Run
Open `index.html` in any browser (double-click it, or right-click → Open With → your browser). No build step, no server, no dependencies needed — just keep `index.html` and `style.css` in the same folder.

## What I Learned This Week
I went in thinking LangChain and LangGraph were basically the same tool with two different names. By the end of the week the real difference was clear: LangChain gives me reusable pieces for talking to a model (templates, parsers, memory, tools), while LangGraph lets those pieces make decisions — branching, looping, and routing — instead of just running in a fixed order every time. That distinction made the orchestrator pattern click for me: it's just a routing node built on top of everything else from the week, which is exactly what our next project needs.
