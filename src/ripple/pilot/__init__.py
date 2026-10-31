"""Pilot operations (claim C3, docs/04 "Pilot metrics"): the weekly report over the
store, the delivery log and the feedback table (ADR-0106).

Reads only. Nothing here writes to the store or sends anything; the report's one side
effect is a folder under results/pilot/<week>/ so every number traces to a file (I8).
"""
