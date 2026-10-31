# Benchmark summary — 2026-10-31_benchsummary_uncommitted

Means over generator seeds, [min to max] when the seeds differ. Scripted oracle resolver, synthetic data, 0 LLM calls (see each run's config.json).

| suite | split | strategy | ablation | seeds | passed | update_accuracy | dependent_update_accuracy | stale_kept | wrongful_changes | questions_asked | questions_needed | stale_retrieval_rate | stale_recommendation_rate | ttc_share_never_converged | cost_per_ripple | resolver_calls_per_scenario |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| finance_v1 | test | append_only | - | 3 | 0.0/35 | 24.3% [23.8% to 24.8%] | 13.5% [13.3% to 13.7%] | 2.23 [2.17 to 2.29] | 0.00 | 0.00 | 0.14 | 32.8% [32.2% to 33.4%] | n/a | 75.7% [75.2% to 76.2%] | 0.00 | 0.00 |
| finance_v1 | test | check_everything | - | 3 | 30.0/35 | 95.2% [95.1% to 95.2%] | 93.2% [93.2% to 93.3%] | 0.14 | 0.00 | 0.14 | 0.14 | 0.0% | n/a | 4.8% [4.8% to 4.9%] | 3.07 [3.02 to 3.11] | 3.94 [3.89 to 4.00] |
| finance_v1 | test | newest_wins | - | 3 | 0.0/35 | 34.0% [33.3% to 34.7%] | 13.5% [13.3% to 13.7%] | 1.94 [1.89 to 2.00] | 0.00 | 0.00 | 0.14 | 32.0% [31.3% to 32.6%] | n/a | 66.0% [65.3% to 66.7%] | 0.00 | 0.00 |
| finance_v1 | test | ripple | - | 3 | 35.0/35 | 100.0% | 100.0% | 0.00 | 0.00 | 0.14 | 0.14 | 0.0% | n/a | 0.0% | 1.53 [1.51 to 1.56] | 1.97 [1.94 to 2.00] |
| finance_v1 | test | ripple | no_ask_user | 3 | 30.0/35 | 82.5% [81.0% to 84.2%] | 81.1% [80.0% to 82.2%] | 0.51 [0.46 to 0.57] | 0.00 | 0.00 | 0.14 | 2.8% [2.1% to 3.5%] | n/a | 17.5% [15.8% to 19.0%] | 1.62 | 1.86 |
| finance_v1 | test | ripple | no_graph | 3 | 30.0/35 | 95.2% [95.1% to 95.2%] | 93.2% [93.2% to 93.3%] | 0.14 | 0.00 | 0.14 | 0.14 | 0.0% | n/a | 4.8% [4.8% to 4.9%] | 3.07 [3.02 to 3.11] | 3.94 [3.89 to 4.00] |
| news_v1 | all | append_only | - | 3 | 0.0/35 | 24.8% [24.3% to 25.3%] | 13.7% [13.5% to 13.9%] | 2.17 [2.11 to 2.23] | 0.00 | 0.00 | 0.14 | 33.6% [33.0% to 34.2%] | n/a | 75.2% [74.7% to 75.7%] | 0.00 | 0.00 |
| news_v1 | all | check_everything | - | 3 | 30.0/35 | 95.1% [95.1% to 95.2%] | 93.1% [93.1% to 93.2%] | 0.14 | 0.00 | 0.14 | 0.14 | 0.0% | n/a | 4.9% [4.8% to 4.9%] | 3.02 [2.98 to 3.07] | 3.89 [3.83 to 3.94] |
| news_v1 | all | newest_wins | - | 3 | 0.0/35 | 34.7% [34.0% to 35.4%] | 13.7% [13.5% to 13.9%] | 1.89 [1.83 to 1.94] | 0.00 | 0.00 | 0.14 | 32.8% [32.1% to 33.5%] | n/a | 65.3% [64.6% to 66.0%] | 0.00 | 0.00 |
| news_v1 | all | ripple | - | 3 | 35.0/35 | 100.0% | 100.0% | 0.00 | 0.00 | 0.14 | 0.14 | 0.0% | n/a | 0.0% | 1.51 [1.49 to 1.53] | 1.94 [1.91 to 1.97] |
| news_v1 | test | append_only | - | 3 | 0.0/20 | 24.6% [21.3% to 29.6%] | 12.4% [9.1% to 17.9%] | 2.17 [1.90 to 2.40] | 0.00 | 0.00 | 0.10 | 34.9% [30.1% to 38.6%] | n/a | 75.4% [70.4% to 78.7%] | 0.00 | 0.00 |
| news_v1 | test | check_everything | - | 3 | 18.0/20 | 96.5% [96.3% to 96.8%] | 95.1% [94.9% to 95.5%] | 0.10 | 0.00 | 0.10 | 0.10 | 0.0% | n/a | 3.5% [3.2% to 3.7%] | 3.31 [3.21 to 3.38] | 3.97 [3.85 to 4.05] |
| news_v1 | test | newest_wins | - | 3 | 0.0/20 | 35.0% [32.8% to 37.0%] | 12.4% [9.1% to 17.9%] | 1.87 [1.70 to 2.05] | 0.00 | 0.00 | 0.10 | 33.9% [30.0% to 37.9%] | n/a | 65.0% [63.0% to 67.2%] | 0.00 | 0.00 |
| news_v1 | test | ripple | - | 3 | 20.0/20 | 100.0% | 100.0% | 0.00 | 0.00 | 0.10 | 0.10 | 0.0% | n/a | 0.0% | 1.57 [1.42 to 1.75] | 1.88 [1.70 to 2.10] |
| news_v1 | test | ripple | no_ask_user | 3 | 18.0/20 | 87.1% [85.2% to 90.2%] | 86.0% [84.6% to 88.6%] | 0.37 [0.30 to 0.40] | 0.00 | 0.00 | 0.10 | 2.2% [1.2% to 2.8%] | n/a | 12.9% [9.8% to 14.8%] | 1.64 [1.45 to 1.86] | 1.80 [1.60 to 2.05] |
| news_v1 | test | ripple | no_graph | 3 | 18.0/20 | 96.5% [96.3% to 96.8%] | 95.1% [94.9% to 95.5%] | 0.10 | 0.00 | 0.10 | 0.10 | 0.0% | n/a | 3.5% [3.2% to 3.7%] | 3.31 [3.21 to 3.38] | 3.97 [3.85 to 4.05] |
| smoke | - | append_only | - | 1 | 0.0/11 | 21.4% | 9.5% | 2.00 | 0.00 | 0.00 | 0.18 | 35.9% | 66.7% | 78.6% | 0.00 | 0.00 |
| smoke | - | check_everything | - | 1 | 8.0/11 | 92.9% | 90.0% | 0.09 | 0.18 | 0.18 | 0.18 | 0.0% | 0.0% | 7.1% | 2.27 | 3.09 |
| smoke | - | newest_wins | - | 1 | 0.0/11 | 28.6% | 9.5% | 1.82 | 0.00 | 0.00 | 0.18 | 34.7% | 50.0% | 71.4% | 0.00 | 0.00 |
| smoke | - | ripple | - | 1 | 11.0/11 | 100.0% | 100.0% | 0.00 | 0.00 | 0.18 | 0.18 | 0.0% | 0.0% | 0.0% | 1.33 | 1.82 |
| v0 | all | append_only | - | 3 | 0.0/35 | 24.6% [24.3% to 24.8%] | 13.6% [13.5% to 13.7%] | 2.19 [2.17 to 2.23] | 0.00 | 0.00 | 0.14 | 33.1% [32.7% to 33.5%] | 66.7% | 75.4% [75.2% to 75.7%] | 0.00 | 0.00 |
| v0 | all | check_everything | - | 3 | 30.0/35 | 95.2% [95.1% to 95.2%] | 93.2% [93.2% to 93.2%] | 0.14 | 0.00 | 0.14 | 0.14 | 0.0% | 0.0% | 4.8% [4.8% to 4.9%] | 3.22 [3.20 to 3.27] | 4.14 [4.11 to 4.20] |
| v0 | all | newest_wins | - | 3 | 0.0/35 | 34.4% [34.0% to 34.7%] | 13.6% [13.5% to 13.7%] | 1.90 [1.89 to 1.94] | 0.00 | 0.00 | 0.14 | 31.4% [31.0% to 31.9%] | 50.0% | 65.6% [65.3% to 66.0%] | 0.00 | 0.00 |
| v0 | all | ripple | - | 3 | 35.0/35 | 100.0% | 100.0% | 0.00 | 0.00 | 0.14 | 0.14 | 0.0% | 0.0% | 0.0% | 1.52 [1.51 to 1.53] | 1.95 [1.94 to 1.97] |
| v0 | test | append_only | - | 3 | 0.0/20 | 19.7% [16.9% to 23.6%] | 9.6% [8.7% to 10.5%] | 2.25 [2.10 to 2.45] | 0.00 | 0.00 | 0.15 [0.10 to 0.25] | 33.1% [32.7% to 33.7%] | 66.7% | 80.3% [76.4% to 83.1%] | 0.00 | 0.00 |
| v0 | test | check_everything | - | 3 | 17.0/20 [15 to 18] | 94.8% [91.8% to 96.4%] | 93.0% [89.1% to 95.2%] | 0.15 [0.10 to 0.25] | 0.00 | 0.15 [0.10 to 0.25] | 0.15 [0.10 to 0.25] | 0.0% | 0.0% | 5.2% [3.6% to 8.2%] | 3.45 [3.22 to 3.75] | 4.30 [4.05 to 4.50] |
| v0 | test | newest_wins | - | 3 | 0.0/20 | 28.7% [23.7% to 36.4%] | 9.6% [8.7% to 10.5%] | 2.00 [1.75 to 2.25] | 0.00 | 0.00 | 0.15 [0.10 to 0.25] | 32.3% [30.3% to 33.4%] | 50.0% | 71.3% [63.6% to 76.3%] | 0.00 | 0.00 |
| v0 | test | ripple | - | 3 | 20.0/20 | 100.0% | 100.0% | 0.00 | 0.00 | 0.15 [0.10 to 0.25] | 0.15 [0.10 to 0.25] | 0.0% | 0.0% | 0.0% | 1.56 [1.50 to 1.67] | 1.95 [1.80 to 2.05] |
| v0 | test | ripple | no_ask_user | 3 | 17.0/20 [15 to 18] | 82.4% [72.9% to 89.1%] | 81.4% [71.7% to 86.8%] | 0.50 [0.30 to 0.80] | 0.00 | 0.00 | 0.15 [0.10 to 0.25] | 2.5% [1.2% to 3.8%] | 0.0% | 17.6% [10.9% to 27.1%] | 1.68 [1.59 to 1.73] | 1.85 [1.75 to 1.90] |
| v0 | test | ripple | no_graph | 3 | 17.0/20 [15 to 18] | 94.8% [91.8% to 96.4%] | 93.0% [89.1% to 95.2%] | 0.15 [0.10 to 0.25] | 0.00 | 0.15 [0.10 to 0.25] | 0.15 [0.10 to 0.25] | 0.0% | 0.0% | 5.2% [3.6% to 8.2%] | 3.45 [3.22 to 3.75] | 4.30 [4.05 to 4.50] |

## Counts per run (mean over seeds, [min to max] when they differ)

| suite | split | strategy | ablation | scenarios | scenarios_passed | errors | resolver_calls | should_change | change_events | recommendations_shown | retrieved |
|---|---|---|---|---|---|---|---|---|---|---|---|
| finance_v1 | test | append_only | - | 35 | 0 | 5 | 0 | 103 [101 to 105] | 40 | 0 | 706.3 [705 to 707] |
| finance_v1 | test | check_everything | - | 35 | 30 | 0 | 138 [136 to 140] | 104 [103 to 105] | 45 | 0 | 567 [564 to 570] |
| finance_v1 | test | newest_wins | - | 35 | 0 | 5 | 0 | 103 [101 to 105] | 40 | 0 | 631 [630 to 632] |
| finance_v1 | test | ripple | - | 35 | 35 | 0 | 69 [68 to 70] | 105 | 45 | 0 | 567 [564 to 570] |
| finance_v1 | test | ripple | no_ask_user | 35 | 30 | 5 | 65 | 103 [101 to 105] | 40 | 0 | 570 |
| finance_v1 | test | ripple | no_graph | 35 | 30 | 0 | 138 [136 to 140] | 104 [103 to 105] | 45 | 0 | 567 [564 to 570] |
| news_v1 | all | append_only | - | 35 | 0 | 5 | 0 | 101 [99 to 103] | 40 | 0 | 675 |
| news_v1 | all | check_everything | - | 35 | 30 | 0 | 136 [134 to 138] | 103 [102 to 104] | 45 | 0 | 541 [539 to 545] |
| news_v1 | all | newest_wins | - | 35 | 0 | 5 | 0 | 101 [99 to 103] | 40 | 0 | 585 |
| news_v1 | all | ripple | - | 35 | 35 | 0 | 68 [67 to 69] | 105 | 45 | 0 | 541 [539 to 545] |
| news_v1 | test | append_only | - | 20 | 0 | 2 | 0 | 57.3 [54 to 61] | 22 | 0 | 391 [342 to 435] |
| news_v1 | test | check_everything | - | 20 | 18 | 0 | 79.3 [77 to 81] | 57.7 [54 to 62] | 24 | 0 | 311.3 [277 to 335] |
| news_v1 | test | newest_wins | - | 20 | 0 | 2 | 0 | 57.3 [54 to 61] | 22 | 0 | 338 [297 to 375] |
| news_v1 | test | ripple | - | 20 | 20 | 0 | 37.7 [34 to 42] | 58 [54 to 63] | 24 | 0 | 311.3 [277 to 335] |
| news_v1 | test | ripple | no_ask_user | 20 | 18 | 2 | 36 [32 to 41] | 57.3 [54 to 61] | 22 | 0 | 314.7 [281 to 337] |
| news_v1 | test | ripple | no_graph | 20 | 18 | 0 | 79.3 [77 to 81] | 57.7 [54 to 62] | 24 | 0 | 311.3 [277 to 335] |
| smoke | - | append_only | - | 11 | 0 | 2 | 0 | 28 | 13 | 3 | 131 |
| smoke | - | check_everything | - | 11 | 8 | 0 | 34 | 28 | 15 | 3 | 93 |
| smoke | - | newest_wins | - | 11 | 0 | 2 | 0 | 28 | 13 | 2 | 118 |
| smoke | - | ripple | - | 11 | 11 | 0 | 20 | 30 | 15 | 3 | 95 |
| v0 | all | append_only | - | 35 | 0 | 5 | 0 | 101.7 [101 to 103] | 40 | 15 | 666.3 [657 to 671] |
| v0 | all | check_everything | - | 35 | 30 | 0 | 145 [144 to 147] | 103.3 [103 to 104] | 45 | 18.3 [18 to 19] | 541 [537 to 545] |
| v0 | all | newest_wins | - | 35 | 0 | 5 | 0 | 101.7 [101 to 103] | 40 | 10 | 606.3 [597 to 611] |
| v0 | all | ripple | - | 35 | 35 | 0 | 68.3 [68 to 69] | 105 | 45 | 18.3 [18 to 19] | 541 [537 to 545] |
| v0 | test | append_only | - | 20 | 0 | 3 [2 to 5] | 0 | 56 [54 to 59] | 22 | 12 [6 to 15] | 408.3 [398 to 425] |
| v0 | test | check_everything | - | 20 | 17 [15 to 18] | 0 | 86 [81 to 90] | 57 [54 to 61] | 25 [24 to 27] | 13 [9 to 16] | 321.7 [308 to 330] |
| v0 | test | newest_wins | - | 20 | 0 | 3 [2 to 5] | 0 | 56 [54 to 59] | 22 | 8 [4 to 10] | 368.3 [357 to 383] |
| v0 | test | ripple | - | 20 | 20 | 0 | 39 [36 to 41] | 58 [54 to 63] | 25 [24 to 27] | 13 [9 to 16] | 321.7 [308 to 330] |
| v0 | test | ripple | no_ask_user | 20 | 17 [15 to 18] | 3 [2 to 5] | 37 [35 to 38] | 56 [54 to 59] | 22 | 11 [6 to 15] | 327 [316 to 334] |
| v0 | test | ripple | no_graph | 20 | 17 [15 to 18] | 0 | 86 [81 to 90] | 57 [54 to 61] | 25 [24 to 27] | 13 [9 to 16] | 321.7 [308 to 330] |

## H1 (ripple / check_everything, ratio of seed means)

| suite | split | accuracy ratio | cost ratio | by seed |
|---|---|---|---|---|
| finance_v1 | test | 105.1% | 50.0% | 20261031: accuracy 105.1% cost 50.0%; 20261032: accuracy 105.0% cost 50.0%; 20261033: accuracy 105.1% cost 50.0% |
| news_v1 | all | 105.1% | 50.0% | 20261031: accuracy 105.1% cost 50.0%; 20261032: accuracy 105.2% cost 50.0%; 20261033: accuracy 105.1% cost 50.0% |
| news_v1 | test | 103.6% | 47.5% | 20261031: accuracy 103.8% cost 44.2%; 20261032: accuracy 103.3% cost 51.9%; 20261033: accuracy 103.6% cost 46.2% |
| v0 | all | 105.1% | 47.1% | 20261019: accuracy 105.1% cost 47.2%; 20261020: accuracy 105.1% cost 47.2%; 20261021: accuracy 105.1% cost 46.9% |
| v0 | test | 105.4% | 45.3% | 20261019: accuracy 103.7% cost 44.4%; 20261020: accuracy 108.9% cost 47.1%; 20261021: accuracy 103.8% cost 44.4% |

## H2 (stale retrieval rate, append_only minus ripple)

| suite | split | append_only | newest_wins | ripple | gap (points) |
|---|---|---|---|---|---|
| finance_v1 | test | 32.8% | 32.0% | 0.0% | 32.8 |
| news_v1 | all | 33.6% | 32.8% | 0.0% | 33.6 |
| news_v1 | test | 34.9% | 33.9% | 0.0% | 34.9 |
| v0 | all | 33.1% | 31.4% | 0.0% | 33.1 |
| v0 | test | 33.1% | 32.3% | 0.0% | 33.1 |

## Source folders

- finance_v1/test/append_only/None: results/2026-10-31_finance_v1_append_only_g20261031_uncommitted, results/2026-10-31_finance_v1_append_only_g20261032_uncommitted, results/2026-10-31_finance_v1_append_only_g20261033_uncommitted
- finance_v1/test/check_everything/None: results/2026-10-31_finance_v1_check_everything_g20261031_uncommitted, results/2026-10-31_finance_v1_check_everything_g20261032_uncommitted, results/2026-10-31_finance_v1_check_everything_g20261033_uncommitted
- finance_v1/test/newest_wins/None: results/2026-10-31_finance_v1_newest_wins_g20261031_uncommitted, results/2026-10-31_finance_v1_newest_wins_g20261032_uncommitted, results/2026-10-31_finance_v1_newest_wins_g20261033_uncommitted
- finance_v1/test/ripple/None: results/2026-10-31_finance_v1_ripple_g20261031_uncommitted, results/2026-10-31_finance_v1_ripple_g20261032_uncommitted, results/2026-10-31_finance_v1_ripple_g20261033_uncommitted
- finance_v1/test/ripple/no_ask_user: results/2026-10-31_finance_v1_ripple_no_ask_user_g20261031_uncommitted, results/2026-10-31_finance_v1_ripple_no_ask_user_g20261032_uncommitted, results/2026-10-31_finance_v1_ripple_no_ask_user_g20261033_uncommitted
- finance_v1/test/ripple/no_graph: results/2026-10-31_finance_v1_ripple_no_graph_g20261031_uncommitted, results/2026-10-31_finance_v1_ripple_no_graph_g20261032_uncommitted, results/2026-10-31_finance_v1_ripple_no_graph_g20261033_uncommitted
- news_v1/all/append_only/None: results/2026-10-31_news_v1_append_only_g20261031_uncommitted_2, results/2026-10-31_news_v1_append_only_g20261032_uncommitted_2, results/2026-10-31_news_v1_append_only_g20261033_uncommitted_2
- news_v1/all/check_everything/None: results/2026-10-31_news_v1_check_everything_g20261031_uncommitted_2, results/2026-10-31_news_v1_check_everything_g20261032_uncommitted_2, results/2026-10-31_news_v1_check_everything_g20261033_uncommitted_2
- news_v1/all/newest_wins/None: results/2026-10-31_news_v1_newest_wins_g20261031_uncommitted_2, results/2026-10-31_news_v1_newest_wins_g20261032_uncommitted_2, results/2026-10-31_news_v1_newest_wins_g20261033_uncommitted_2
- news_v1/all/ripple/None: results/2026-10-31_news_v1_ripple_g20261031_uncommitted_2, results/2026-10-31_news_v1_ripple_g20261032_uncommitted_2, results/2026-10-31_news_v1_ripple_g20261033_uncommitted_2
- news_v1/test/append_only/None: results/2026-10-31_news_v1_append_only_g20261031_uncommitted, results/2026-10-31_news_v1_append_only_g20261032_uncommitted, results/2026-10-31_news_v1_append_only_g20261033_uncommitted
- news_v1/test/check_everything/None: results/2026-10-31_news_v1_check_everything_g20261031_uncommitted, results/2026-10-31_news_v1_check_everything_g20261032_uncommitted, results/2026-10-31_news_v1_check_everything_g20261033_uncommitted
- news_v1/test/newest_wins/None: results/2026-10-31_news_v1_newest_wins_g20261031_uncommitted, results/2026-10-31_news_v1_newest_wins_g20261032_uncommitted, results/2026-10-31_news_v1_newest_wins_g20261033_uncommitted
- news_v1/test/ripple/None: results/2026-10-31_news_v1_ripple_g20261031_uncommitted, results/2026-10-31_news_v1_ripple_g20261032_uncommitted, results/2026-10-31_news_v1_ripple_g20261033_uncommitted
- news_v1/test/ripple/no_ask_user: results/2026-10-31_news_v1_ripple_no_ask_user_g20261031_uncommitted, results/2026-10-31_news_v1_ripple_no_ask_user_g20261032_uncommitted, results/2026-10-31_news_v1_ripple_no_ask_user_g20261033_uncommitted
- news_v1/test/ripple/no_graph: results/2026-10-31_news_v1_ripple_no_graph_g20261031_uncommitted, results/2026-10-31_news_v1_ripple_no_graph_g20261032_uncommitted, results/2026-10-31_news_v1_ripple_no_graph_g20261033_uncommitted
- smoke/None/append_only/None: results/2026-10-31_smoke_append_only_uncommitted
- smoke/None/check_everything/None: results/2026-10-31_smoke_check_everything_uncommitted
- smoke/None/newest_wins/None: results/2026-10-31_smoke_newest_wins_uncommitted
- smoke/None/ripple/None: results/2026-10-31_smoke_uncommitted
- v0/all/append_only/None: results/2026-10-31_v0_append_only_g20261019_uncommitted_2, results/2026-10-31_v0_append_only_g20261020_uncommitted_2, results/2026-10-31_v0_append_only_g20261021_uncommitted_2
- v0/all/check_everything/None: results/2026-10-31_v0_check_everything_g20261019_uncommitted_2, results/2026-10-31_v0_check_everything_g20261020_uncommitted_2, results/2026-10-31_v0_check_everything_g20261021_uncommitted_2
- v0/all/newest_wins/None: results/2026-10-31_v0_newest_wins_g20261019_uncommitted_2, results/2026-10-31_v0_newest_wins_g20261020_uncommitted_2, results/2026-10-31_v0_newest_wins_g20261021_uncommitted_2
- v0/all/ripple/None: results/2026-10-31_v0_ripple_g20261019_uncommitted_2, results/2026-10-31_v0_ripple_g20261020_uncommitted_2, results/2026-10-31_v0_ripple_g20261021_uncommitted_2
- v0/test/append_only/None: results/2026-10-31_v0_append_only_g20261019_uncommitted, results/2026-10-31_v0_append_only_g20261020_uncommitted, results/2026-10-31_v0_append_only_g20261021_uncommitted
- v0/test/check_everything/None: results/2026-10-31_v0_check_everything_g20261019_uncommitted, results/2026-10-31_v0_check_everything_g20261020_uncommitted, results/2026-10-31_v0_check_everything_g20261021_uncommitted
- v0/test/newest_wins/None: results/2026-10-31_v0_newest_wins_g20261019_uncommitted, results/2026-10-31_v0_newest_wins_g20261020_uncommitted, results/2026-10-31_v0_newest_wins_g20261021_uncommitted
- v0/test/ripple/None: results/2026-10-31_v0_ripple_g20261019_uncommitted, results/2026-10-31_v0_ripple_g20261020_uncommitted, results/2026-10-31_v0_ripple_g20261021_uncommitted
- v0/test/ripple/no_ask_user: results/2026-10-31_v0_ripple_no_ask_user_g20261019_uncommitted, results/2026-10-31_v0_ripple_no_ask_user_g20261020_uncommitted, results/2026-10-31_v0_ripple_no_ask_user_g20261021_uncommitted
- v0/test/ripple/no_graph: results/2026-10-31_v0_ripple_no_graph_g20261019_uncommitted, results/2026-10-31_v0_ripple_no_graph_g20261020_uncommitted, results/2026-10-31_v0_ripple_no_graph_g20261021_uncommitted
