# Persistent State Across Scanner Restarts

Save scanner state (active signals, cooldowns, in-flight trade context, last scanned timestamp per instrument) to a local JSON/SQLite store. On restart, the scanner resumes from last known state instead of starting fresh — avoiding duplicate alerts, missed TP/SL updates, and lost trade management context.

## Rationale
When the scanner restarts (due to crash, manual stop, or system reboot), all in-flight trade context is lost. A trader who got a heads-up alert before the restart never gets the confirmed entry or the TP/SL management updates. This breaks the alert lifecycle and erodes trust in the system.

## User Stories
- As a trader, I want the scanner to remember my active trade alerts after a restart so that I continue receiving TP/SL management updates
- As a trader, I don't want to receive duplicate Telegram alerts after restarting the scanner

## Acceptance Criteria
- [ ] Scanner state is persisted to disk every scan cycle (every 60 seconds)
- [ ] On restart, scanner loads last state and resumes cooldowns, active signals, and trade management
- [ ] Duplicate alerts are suppressed for signals that were already sent before the restart
- [ ] State file is human-readable JSON with clear schema documentation
- [ ] Graceful degradation: if state file is corrupted, scanner starts fresh with a warning log
