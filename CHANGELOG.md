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
