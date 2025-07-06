# CHANGELOG

<!-- version list -->

## v2.2.0 (2025-07-06)

### Features

- Apply random schedule to update-mirrors command
  ([#17](https://github.com/cagojeiger/cli-git/pull/17),
  [`21b073c`](https://github.com/cagojeiger/cli-git/commit/21b073c3d179c8e25b211fe4ef88568623ad9eab))


## v2.1.1 (2025-07-06)

### Bug Fixes

- Support recursive directory backup in .mirrorkeep
  ([#16](https://github.com/cagojeiger/cli-git/pull/16),
  [`3085694`](https://github.com/cagojeiger/cli-git/commit/3085694016f4dfe92f9e81554723b049182ca9b5))


## v2.1.0 (2025-07-06)

### Bug Fixes

- Replace rebase with reset to avoid modify/delete conflicts
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Restore original directory after os.chdir in workflow_updater
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

### Features

- Add edge case handling and documentation for mirrorkeep
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Add mirrorkeep parser module with pattern matching
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Add random bi-weekly schedule for mirror sync
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Implement .mirrorkeep file preservation system
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Mirrorkeep 파일 시스템 구현 및 랜덤 스케줄 기능 추가 ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

- Update workflow to use .mirrorkeep for file preservation
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))

### Refactoring

- Apply Occam's Razor to complete_repository function
  ([#9](https://github.com/cagojeiger/cli-git/pull/9),
  [`bd07b15`](https://github.com/cagojeiger/cli-git/commit/bd07b1543b9ea87208a2ca72301cd6653ce670be))

- Extract workflow template to external file ([#13](https://github.com/cagojeiger/cli-git/pull/13),
  [`67f0fff`](https://github.com/cagojeiger/cli-git/commit/67f0fff4888a8c64e3b18dc68f0e490568dc0536))

- Simplify init_command by extracting helper functions
  ([#12](https://github.com/cagojeiger/cli-git/pull/12),
  [`63f34ab`](https://github.com/cagojeiger/cli-git/commit/63f34ab5008aa189815f7286ae4605ca0de0a0e7))

- Simplify workflow by applying Occam's razor principle
  ([#15](https://github.com/cagojeiger/cli-git/pull/15),
  [`abbe82b`](https://github.com/cagojeiger/cli-git/commit/abbe82b8abc11fbd8959beed683589b88ddf4d4b))


## v2.0.0 (2025-07-02)

### Bug Fixes

- Resolve GitHub token permission issues for tag sync
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Resolve update-mirrors command issues ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

### Chores

- Remove macOS from CI to reduce costs ([#6](https://github.com/cagojeiger/cli-git/pull/6),
  [`ce62bed`](https://github.com/cagojeiger/cli-git/commit/ce62bed5f53a8b7937c592745a9eed4c4794d142))

### Features

- Add GitHub Personal Access Token support for tag synchronization
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Add repository autocompletion and improve update-mirrors UX
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Add update-mirrors command for existing mirror migration
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Improve update-mirrors command and add token info to info command
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

### Refactoring

- Apply Occam's razor to update-mirrors command ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Separate scan functionality from update in update-mirrors command
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

- Simplify update-mirrors command and improve caching
  ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))

### Testing

- Add tests to improve code coverage to 85% ([#8](https://github.com/cagojeiger/cli-git/pull/8),
  [`2915139`](https://github.com/cagojeiger/cli-git/commit/2915139cca8d4796f1c66d6c99d1239083891175))


## v1.2.0 (2025-06-28)

### Bug Fixes

- Improve mirror functionality robustness and code quality
  ([#5](https://github.com/cagojeiger/cli-git/pull/5),
  [`162aeb7`](https://github.com/cagojeiger/cli-git/commit/162aeb72e36f54356d5ffa876f6148b433336951))

- Improve mirror sync robustness and error handling
  ([#5](https://github.com/cagojeiger/cli-git/pull/5),
  [`162aeb7`](https://github.com/cagojeiger/cli-git/commit/162aeb72e36f54356d5ffa876f6148b433336951))

### Features

- Enhance mirror functionality with dynamic branch detection and .github cleanup
  ([#5](https://github.com/cagojeiger/cli-git/pull/5),
  [`162aeb7`](https://github.com/cagojeiger/cli-git/commit/162aeb72e36f54356d5ffa876f6148b433336951))


## v1.1.1 (2025-06-28)

### Bug Fixes

- Replace hardcoded 'main' branch with dynamic branch detection
  ([#4](https://github.com/cagojeiger/cli-git/pull/4),
  [`0950b5b`](https://github.com/cagojeiger/cli-git/commit/0950b5b397e8cdc87394066612d614d6a1b34916))


## v1.1.0 (2025-06-28)

### Bug Fixes

- Add permissions and improve Slack notifications for mirror sync
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Address CI failures and deprecation warnings ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Adjust test coverage requirement to 86% ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Commit workflow changes before pushing to prevent original actions from running
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Complete test fixes for Phase 3 features ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Lower coverage requirement to 70% for Phase 3 ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Phase 3 보완 - 벨리데이션 강화 및 테스트 구조 개선 ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Use shlex.split() for proper git command parsing
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

### Documentation

- Add context management guidelines and private-mirror plan
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Simplify context files and add Occam's Razor principle
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

### Features

- Add init and info commands for user configuration
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Add Phase 3 features - enhanced UX and automation
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Add private-mirror command for open source analysis
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Implement private-mirror command for repository mirroring
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Improve init command UX with auto-login and visible webhook input
  ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))

- Show help by default and simplify README ([#3](https://github.com/cagojeiger/cli-git/pull/3),
  [`0dcff84`](https://github.com/cagojeiger/cli-git/commit/0dcff84005786dfe7315650078dedde7d548601f))


## v1.0.0 (2025-06-27)

- Initial Release
