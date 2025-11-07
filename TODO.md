# Fireteam TODO

## Testing Improvements

### Non-Happy-Path Testing
- [ ] Test invalid goals (empty, malformed)
- [ ] Test API failure handling (rate limits, network errors)
- [ ] Test timeout handling (partial completion)
- [ ] Test cleanup on errors (state files, git repos)
- [ ] Test concurrent runs (multiple Fireteam instances)

### Performance & Observability
- [ ] Add performance benchmarks
  - Track cycle count over time
  - Track API token usage per task
  - Track completion times by task complexity
- [ ] Add test result dashboard/reporting
- [ ] Add metrics collection for production runs

### Terminal-bench Coverage
- [ ] Test on medium complexity tasks
- [ ] Test on multi-file tasks
- [ ] Measure accuracy across full task suite
- [ ] Add regression tests for known-good tasks
- [ ] Benchmark against other agents

