# Clipfarm v0.9.1 Structural Repair

Reorganized the flattened repository into the `src/clipfarm` package layout required by `pyproject.toml` and the project's imports.

- Python compileall: PASS
- Pytest return code: 1

## Pytest output

```
[32m.[0m[32m.[0m[31mF[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[31m                                                            [100%][0m
=================================== FAILURES ===================================
[31m[1m__________________ test_edit_plan_has_tightening_and_emphasis __________________[0m

    [0m[94mdef[39;49;00m[90m [39;49;00m[92mtest_edit_plan_has_tightening_and_emphasis[39;49;00m():[90m[39;49;00m
        plan = build_edit_plan(candidate(), transcript())[90m[39;49;00m
        [94massert[39;49;00m plan[[33m"[39;49;00m[33mend[39;49;00m[33m"[39;49;00m] >= [94m15.0[39;49;00m[90m[39;49;00m
        [94massert[39;49;00m [96misinstance[39;49;00m(plan[[33m"[39;49;00m[33mtighten_edits[39;49;00m[33m"[39;49;00m], [96mlist[39;49;00m)[90m[39;49;00m
>       [94massert[39;49;00m [96many[39;49;00m(e[[33m"[39;49;00m[33mword[39;49;00m[33m"[39;49;00m].lower().startswith([33m"[39;49;00m[33mkey[39;49;00m[33m"[39;49;00m) [94mfor[39;49;00m e [95min[39;49;00m plan[[33m"[39;49;00m[33mcaption_emphasis[39;49;00m[33m"[39;49;00m])[90m[39;49;00m
[1m[31mE       assert False[0m
[1m[31mE        +  where False = any(<generator object test_edit_plan_has_tightening_and_emphasis.<locals>.<genexpr> at 0x7faf6ffe9f10>)[0m

[1m[31mtests/test_editing_intelligence.py[0m:48: AssertionError
[36m[1m=========================== short test summary info ============================[0m
[31mFAILED[0m tests/test_editing_intelligence.py::[1mtest_edit_plan_has_tightening_and_emphasis[0m - assert False
 +  where False = any(<generator object test_edit_plan_has_tightening_and_emphasis.<locals>.<genexpr> at 0x7faf6ffe9f10>)
[31m[31m[1m1 failed[0m, [32m12 passed[0m[31m in 0.16s[0m[0m
Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/generated/interface/models.py", line 32317, in hydrate_crdt_from_proto
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.

```
