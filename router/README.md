# Router

Self-contained component. Runs separately from the main SafeClaw app. Can run on another process or machine on the same network.

## Setup

```bash
cd router
pip install -r requirements.txt
```

Copy `.env` and set `REDIS_URL` (e.g. `redis://host:6379/0`).

## Run

From router directory:
```bash
cd router
python start_router.py
```

Or:
```bash
./start_router.py
```

## Structure

```
router/
  start_router.py   # Entry point
  .env              # REDIS_URL, COMMAND_QUEUE, RESPONSE_PREFIX
  libs/
    router.py       # Router class
    base_skill.py
  skills/
    create_post/
      skill.py
```

See router_design_details.txt for full design documentation.
