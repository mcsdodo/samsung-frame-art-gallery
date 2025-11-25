# Samsung Frame TV Art Mode Verification Design

**Date:** 2025-11-25
**Status:** Approved
**Goal:** Verify communication with Samsung Frame TV art mode before building the web application

## Overview

Create a Docker-based verification script that confirms we can communicate with the Samsung Frame TV's art mode API. This is a prerequisite step before implementing the full web application.

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runtime | Docker | Consistent environment, smooth transition to web app |
| Base image | python:3.11-slim | Balance of size (~150MB) and compatibility |
| Library | NickWaterton/samsung-tv-ws-api | More mature, better documented art mode support |
| Network | Host mode | Required for local network TV access |

## Project Structure

```
samsung-frame-art-gallery/
├── docker/
│   └── Dockerfile
├── src/
│   └── verify_tv.py
├── docker-compose.yml
├── requirements.txt
├── docs/
│   └── plans/
│       └── 2025-11-25-tv-verification-design.md
└── _tasks/
    └── 01-task.md
```

## Components

### 1. Dockerfile (`docker/Dockerfile`)

- Base: `python:3.11-slim`
- Install library from GitHub via pip
- Copy source into `/app`
- Entrypoint: `python verify_tv.py`

### 2. Verification Script (`src/verify_tv.py`)

**Sequence:**
1. Connect to TV at configured IP (default: 192.168.0.105)
2. Call `art().supported()` to check art mode availability
3. If supported, retrieve:
   - Available art mode API methods
   - Current artwork info (if displaying)
   - List of artwork on TV
4. Print structured results with PASS/FAIL status

**Error Handling:**
- 10-second connection timeout
- Graceful handling if TV is off/unreachable
- Full error details captured and displayed

**Output Format:**
- Clear section headers
- JSON-formatted API responses
- Explicit PASS/FAIL for each check

### 3. Docker Compose (`docker-compose.yml`)

```yaml
services:
  verify:
    build:
      context: .
      dockerfile: docker/Dockerfile
    network_mode: host
    environment:
      - TV_IP=192.168.0.105
```

### 4. Dependencies (`requirements.txt`)

```
git+https://github.com/NickWaterton/samsung-tv-ws-api.git
```

**Fallback:** If NickWaterton's library fails, try xchwarze/samsung-tv-ws-api fork.

## Usage

```bash
# Build and run verification
docker-compose up --build

# With different TV IP
TV_IP=192.168.0.100 docker-compose up --build
```

## Success Criteria

- [ ] Container builds successfully
- [ ] Connects to TV at 192.168.0.105
- [ ] `art().supported()` returns True
- [ ] Art mode features are listed
- [ ] Current artwork state is retrieved

## Next Steps

After successful verification:
1. Design the web application architecture
2. Implement image browsing UI
3. Add image upload to TV functionality
