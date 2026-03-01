# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- (add changes here)

### Changed
- (add changes here)

### Fixed
- (add fixes here)

---

## [1.0.43] - 2026-03-01

### Added
- Add option parameter to chat function in llm. so that for different llm it accept prompt with option operation

---

## [1.0.42] - 2026-02-27

### Added
- (add changes here)

### Changed
- (add changes here)

### Fixed
- (add fixes here)

---

## [1.0.41] - 2026-02-27

### Changed
- Take out <artifact> as input history is enough for short memory. 

### Fixed
- Fix too long prompt to make the request prompt to llm truncated

---

## [1.0.40] - 2026-02-26

### Fixed
- agent clear should remove schedule.json

---

## [1.0.39] - 2026-02-26

### Changed
- Refine PROMPT.md

---

## [1.0.38] - 2026-02-26

### Added
- Headless channel so that it provide interface for other LAN service to interact with agent

### Changed
- Adjust PROMPT

---

## [1.0.37] - 2026-02-25

### Fixed
- Skill fail return handling

---

## [1.0.36] - 2026-02-25

### Added
- Router action will return with {"text":???, "instruction":???, "data":???}
  So text will be display message; instruction is ask llm how to use the data

---

## [1.0.35] - 2026-02-24

### Fixed
- Process message sometime after the final response. 

---

## [1.0.34] - 2026-02-24

### Changed
- Folder changed

---

## [1.0.33] - 2026-02-24

### Added
- Add local gemini bridge llm extended class

### Changed
- Take out PROMPT.md from /workspace and clone to under llm extended class folder for llm prompt tuning
- Gemini prompt tuning

---

## [1.0.32] - 2026-02-23

### Added
- Scheduler now support 'prompt'

---

## [1.0.31] - 2026-02-23

### Fixed
- Scheduler date time and relative time handling for llm

---

## [1.0.30] - 2026-02-23

### Added
- Scheduler now support 'action'

### Fixed
- Console You: prompt need to resume when other broadcast messages

---

## [1.0.29] - 2026-02-23

### Added
- _BROADCAST_MSG agent action
- Schedule reminder implementation

---

## [1.0.28] - 2026-02-23

### Added
- (add changes here)

### Changed
- (add changes here)

### Fixed
- (add fixes here)

---

## [1.0.27] - 2026-02-23

### Added
- (add changes here)

### Changed
- (add changes here)

### Fixed
- (add fixes here)

---

## [1.0.26] - 2026-02-23

### Added
- command /schedule to list schedules 

---

## [1.0.25] - 2026-02-23

### Added
- schedule.json in workspace to store future schedules for the agent

### Changed
- scheduler will get schedule in the json 

---

## [1.0.24] - 2026-02-23

### Added
- Tick mechanism for agent for future scheduler
- Add agent action ADD_SCHEDULE and DELETE_SCHEDULE

---

## [1.0.23] - 2026-02-23

### Fixed
- roll_back_version.sh not clear added files

---

## [1.0.22] - 2026-02-20

### Fixed
- /restart not work and make process corrupted

---

## [1.0.21] - 2026-02-20

### Added
- /restart command to allow to restart the server (use for changing settings or configuration)

---

## [1.0.20] - 2026-02-20

### Added
- command.py in libs to define system command that channels can call and get response

### Changed
- Readme.md and help text file

---

## [1.0.19] - 2026-02-20

### Added
- Commands of telegram bot

### Changed
- Add mechanism to handle command in telegram including (/whoami, /memory, /soul)

---

## [1.0.18] - 2026-02-20

### Added
- "thinking" settings in config.json in agent

### Changed
- if "thinking" is enabled, show the processing message so that user can see what is happening

---

## [1.0.17] - 2026-02-20

### Added
- llm.log to log down user input and llm raw response

---

## [1.0.16] - 2026-02-20

### Fixed
- Refine artifact.json output

---

## [1.0.15] - 2026-02-20

### Added
- N/A

### Changed
- file name of router_action(s).json and router_action(s)_initial.json will be removed with 's'

### Fixed
- N/A

---

## [1.0.14] - 2026-02-20

### Added
- N/A

### Changed
- Artifct and output files update for Browser Vision

### Fixed
- N/A

---

## [1.0.13] - 2026-02-20

### Added
- Parameters for browser vision

### Changed
- Enhance the browser vision features

### Fixed
- N/A

---

## [1.0.12] - 2026-02-20

### Added
- (add changes here)

### Changed
- Move base llm class to libs instead in llm folder 

### Fixed
- Follow-up action not working

---

## [1.0.11] - 2026-02-20

### Added
- Agent action decoupling with action_executor. It will put in ability folder
- Base classs of agent action 

### Changed
- Dynamic map agent action in ability class

### Fixed
- (add fixes here)

---

## [1.0.10] - 2026-02-19

### Added
- N/A

### Changed
- N/A

### Fixed
- Channels should know typing state if input request is not in that channel

---

## [1.0.9] - 2026-02-19

### Added
- Hello World default skill in router

### Changed
- Structure of config.json in router
- Change start up prompt for agent and router

### Fixed
- N/A

---

## [1.0.8] - 2026-02-18

### Added
- Add AgentConfig Class for config.json

### Changed
- N/A

### Fixed
- N/A

---

## [1.0.7] - 2026-02-18

### Added
- Add llm folder in agent to make different llm to locate
- Add Ollama LLM as default llm
- Create OllamaLLM class 

### Changed
- N/A

### Fixed
- N/A

---

## [1.0.6] - 2026-02-18

### Added
- N/A

### Changed
- Change some configure files and md files location to a better place

### Fixed
- N/A

---

## [1.0.5] - 2026-02-18

### Added
- Add base agent class
- Add channels to base agent class
- Add console channel as default channel
- Add telegram channel which is configurable in config.json

### Changed
- Refine class structure and channel structure
- Refine utils function for llm and encapulate to base llm class
- Refine logging for agent

### Fixed
- N/A

---

## [1.0.4] - 2026-02-17

### Added
- agent/libs/llm_client.py

### Changed
- Add LLM config to .env.sample (and .env)

### Fixed
- N/A

---

## [1.0.3] - 2026-02-17

### Added
- N/A

### Changed
- chat.py

### Fixed
- Warning for urllib3 ignored

---

## [1.0.2] - 2026-02-17

### Added
- N/A

### Changed
- push_new_version.sh

### Fixed
- Fix push_new_version.sh not remove and add file

---

## [1.0.1] - 2026-02-17

### Added
- router config_initial.json

### Changed
- Router start will load config.json in object. if not found, it will clone a config.json from config_initial.json

### Fixed
- N/A

---

## [1.0.0] - 2026-02-17

### Added
- Version management with push_new_version.sh and roll_back_version.sh

### Changed
- N/A

### Fixed
- N/A

---
