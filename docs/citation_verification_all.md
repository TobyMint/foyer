# refs.bib 46 条逐条引用核验（Crossref / Semantic Scholar / OpenAlex 三源）

生成脚本：`docs/citation_verify_all.py`（从仓库根目录跑，可复现）。

**判定口径**：每个字段**单独判**，不写「差不多就算过」。`?` = 该源无此字段或写法差异大到无法判（**不是**通过）；`~` = 部分相符；`✗` = 不符。

⚠ **本环境查不到的源**（不许当成「查过了」）：`dblp.org` 直连失败；`export.arxiv.org/api` 只回 301 空体 —— 故 arXiv-only 条目走 S2 的 `arXiv:<id>` 入口。

生成时间：2026-09-27 19:37 CST

命中：Crossref **25**/31（有 DOI 的条目）｜Semantic Scholar **29**/46｜OpenAlex **44**/46。


## `sarathi`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Taming {Throughput-Latency} Tradeoff in {LLM} Inference with {Sarathi-Serve} | — | — | — |
| 年 | 2024 | — | — | — |
| 作者 | Agrawal, Amey and Kedia, Nitin and Panwar, Ashish and Mohan, Jayashree and Kwatra, Nipun and Gulavani, Bhargav and Tumanov, Alexey and Ramjee, Ramachandran | — | — | — |
| venue | 18th USENIX Symposium on Operating Systems Design and Implementation (OSDI '24) | — | — | — |
| 页码 | 117--134 | — | — | — |
| DOI | None | 无 DOI 字段 | — | — |

**判定**：标题 ✗0.00 ｜ 年 ? ｜ 作者 ? ｜ 页码 ?


## `distserve`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {DistServe}: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving | — | — | DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving |
| 年 | 2024 | — | — | 2024 |
| 作者 | Zhong, Yinmin and Liu, Shengyu and Chen, Junda and Hu, Jianbo and Zhu, Yibo and Liu, Xuanzhe and Jin, Xin and Zhang, Hao | — | — | Yinmin Zhong; Shengyu Liu; Junda Chen; Hu, Jianbo; Yibo Zhu; Xuanzhe Liu; Xin Jin; Hao Zhang |
| venue | 18th USENIX Symposium on Operating Systems Design and Implementation (OSDI '24) | — | — | arXiv (Cornell University) |
| 页码 | 193--210 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2401.09670 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ~(6/8) ｜ 页码 ?


## `mooncake`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Mooncake: A {KVCache-centric} Disaggregated Architecture for {LLM} Serving | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving |
| 年 | 2026 | 2026 | 2024 | 2025 |
| 作者 | Qin, Ruoyu and Li, Zheming and He, Weiran and Cui, Jialei and Tang, Heyi and Ren, Feng and Ma, Teng and Cai, Shangming and Zhang, Yineng and Zhang, Mingxing and Wu, Yongwei and Zheng, Weimin and Xu, Xinran | Qin, Ruoyu; Li, Zheming; He, Weiran; Cui, Jialei; Tang, Heyi; Ren, Feng; Ma, Teng; Cai, Shangming; Zhang, Yineng; Zhang, Mingxing; Wu, Yongwei; Zheng, Weimin; Xu, Xinran | Ruoyu Qin; Zhe-Ming Li; Wei-Ran He; Jia-Lei Cui; He-Yi Tang; Feng Ren; Teng Ma; Shangming Cai; Yineng Zhang; Mingxing Zhang; Yong-Wei Wu; Wei-Min Zheng; Xinran Xu | Ruoyu Qin; Zheming Li; Weiran He; Jialei Cui; Heyi Tang; Feng Ren; Teng Ma; Shangming Cai; Y X Zhang; Mingxing Zhang; Yongwei Wu; Weimin Zheng; Xinran Xu |
| venue | ACM Transactions on Storage | ACM Transactions on Storage | ACM Transactions on Storage | ACM Transactions on Storage |
| 页码 | 1--38 | 1-38 | 1 - 38 | 1--38 |
| DOI | 10.1145/3773772 | ✓ 解析成功 | 10.1145/3773772 | 10.1145/3773772 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `concur`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {CONCUR}: High-Throughput Agentic Batch Inference of {LLM} via Congestion-Based Concurrency Control | — | — | — |
| 年 | 2026 | — | — | — |
| 作者 | Chen, Qiaoling and Ye, Zhisheng and Tang, Tian and Sun, Peng and Tian, Boyu and Wang, Guoteng and Li, Shenggui and Wen, Yonggang and Han, Zhenhua and Zhang, Tianwei | — | — | — |
| venue | International Conference on Machine Learning (ICML 2026) | — | — | — |
| 页码 | None | — | — | — |
| DOI | None | 无 DOI 字段 | — | — |

**判定**：标题 ✗0.00 ｜ 年 ? ｜ 作者 ?


## `continuum`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Continuum: Efficient and Robust Multi-Turn {LLM} Agent Scheduling with {KV} Cache Time-to-Live | — | Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live | Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live |
| 年 | 2025 | — | 2025 | 2025 |
| 作者 | Li, Hanchen and He, Runyuan and Mang, Qiuyang and Zhang, Qizheng and Mao, Huanzhi and Chen, Xiaokun and Zhou, Hangrui and Zhang, Huanchen and Cheung, Alvin and Gonzalez, Joseph and Stoica, Ion | — | Han-Chen Li; Runyuan He; Qiuyang Mang; Qizheng Zhang; Huanzhi Mao; Xiaokun Chen; Hang-Rui Zhou; Huan-Chen Zhang; Alvin Cheung; Joseph Gonzalez; Ion Stoica | Li, Hanchen; He, Runyuan; Mang, Qiuyang; Zhang, Qizheng; Mao, Huanzhi; Chen, Xiaokun; Zhou, Hangrui; Zhang, Huanchen; Cheung, Alvin; Gonzalez, Joseph; Stoica, Ion |
| venue | None | — | arXiv.org | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2511.02230 | ✗ 查不到 | 10.48550/arXiv.2511.02230 | 10.48550/arxiv.2511.02230 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `thunderagent`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {ThunderAgent}: A Simple, Fast and Program-Aware Agentic Inference System | — | — | ThunderAgent: A Simple, Fast and Program-Aware Agentic Inference System |
| 年 | 2026 | — | — | 2026 |
| 作者 | Kang, Hao and Li, Ziyang and Xu, Weili and Yang, Xinyu and Chen, Yinfang and Wang, Junxiong and Chen, Beidi and Krishna, Tushar and Xu, Chenfeng and Arora, Simran | — | — | Hao Kang; Ziyang Li; Weili Xu; Xinyu Yang; Yinfang Chen; Junxiong Wang; Beidi Chen; Tushar Krishna; Chenfeng Xu; Simran Arora |
| venue | None | — | — | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2602.13692 | ✗ 查不到 | — | 10.48550/arxiv.2602.13692 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `talaria`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Talaria: Session-Aware Serverless Serving of Hundred-Billion-Parameter {LLMs} | — | Talaria: Session-Aware Serverless Serving of Hundred-Billion-Parameter LLMs | Talaria: Session-Aware Serverless Serving of Hundred-Billion-Parameter LLMs |
| 年 | 2026 | — | 2026 | 2026 |
| 作者 | Meng, Utopia and Zhao, Unicornt and Li, Derek and Gao, Goalen and Du, Frank | — | Utopia Meng; Unicornt Zhao; Derek Li; Goalen Gao; Frank Du | Utopia Meng; Unicornt Zhao; Derek Li; Goalen Gao; Frank Du |
| venue | None | — | arXiv.org | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2607.17181 | ✗ 查不到 | 10.48550/arXiv.2607.17181 | 10.48550/arxiv.2607.17181 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `mori`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with {MORI} | — | Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with MORI | Idleness is Relative: Exploiting Tool-Call Idle Windows for Offloading in Agentic Systems with MORI |
| 年 | 2026 | — | 2026 | 2026 |
| 作者 | Xia, Tian and Li, Hanchen and Li, Zhifei and Chen, Xiaokun and Kang, Hao and Qiao, Yifan and Xu, Yi and Stoica, Ion | — | Tian Xia; Han-Chen Li; Zhifei Li; Xiaokun Chen; Hao Kang; Yifan Qiao; Yi Xu; Ion Stoica | Tian Xia; Hanchen Li; Zhifei Li; Xiaokun Chen; Hao Kang; Yifan Qiao; Yi Xu; Ion Stoica |
| venue | None | — | arXiv.org | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2606.00866 | ✗ 查不到 | 10.48550/arXiv.2606.00866 | 10.48550/arxiv.2606.00866 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `zhu2026tracelab`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {TraceLab}: Characterizing Coding Agent Workloads for {LLM} Serving | — | — | TraceLab: Characterizing Coding Agent Workloads for LLM Serving |
| 年 | 2026 | — | — | 2026 |
| 作者 | Zhu, Kan and Jacob, Mathew and Ma, Chenxi and Pan, Yi and Wang, Stephanie and Krishnamurthy, Arvind and Kasikci, Baris | — | — | Kan Zhu; Mathew Jacob; Chenxi Ma; Yi Pan; Stephanie Wang; Arvind Krishnamurthy; Baris Kasikci |
| venue | None | — | — | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2606.30560 | ✗ 查不到 | — | 10.48550/arxiv.2606.30560 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `zheng2024sglang`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {SGLang}: Efficient Execution of Structured Language Model Programs | — | SGLang: Efficient Execution of Structured Language Model Programs | SGLang: Efficient Execution of Structured Language Model Programs |
| 年 | 2024 | — | 2023 | 2024 |
| 作者 | Zheng, Lianmin and Yin, Liangsheng and Xie, Zhiqiang and Sun, Chuyue and Huang, Jeff and Yu, Cody Hao and Cao, Shiyi and Kozyrakis, Christos and Stoica, Ion and Gonzalez, Joseph E. and Barrett, Clark and Sheng, Ying | — | Lian-Min Zheng; Liangsheng Yin; Zhiqiang Xie; Chu-Yue Sun; Jeff Huang; C. Yu; Shiyi Cao; Christoforos E. Kozyrakis; Ion Stoica; Joseph E. Gonzalez; Clark W. Barrett; Ying Sheng | Lianmin Zheng; Liangsheng Yin; Zhiqiang Xie; Chuyue Sun; Jeff Huang; Cody Yu; Shiyi Cao; Christos Kozyrakis; Ion Gabriel Stoica; Joseph E. Gonzalez; Clark Barrett; Ying Sheng |
| venue | Advances in Neural Information Processing Systems 37 (NeurIPS 2024) | — | Neural Information Processing Systems | — |
| 页码 | 62557--62583 | — | — | 62557--62583 |
| DOI | None | 无 DOI 字段 | 10.52202/079017-2000 | 10.52202/079017-2000 |

**判定**：标题 ✓ ｜ 年 ✗(2023) ｜ 作者 ✓ ｜ 页码 ✓


## `kwon2023pagedattention`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Efficient Memory Management for Large Language Model Serving with {PagedAttention} | Efficient Memory Management for Large Language Model Serving with PagedAttention | Efficient Memory Management for Large Language Model Serving with PagedAttention | Efficient Memory Management for Large Language Model Serving with PagedAttention |
| 年 | 2023 | 2023 | 2023 | 2023 |
| 作者 | Kwon, Woosuk and Li, Zhuohan and Zhuang, Siyuan and Sheng, Ying and Zheng, Lianmin and Yu, Cody Hao and Gonzalez, Joseph E. and Zhang, Hao and Stoica, Ion | Kwon, Woosuk; Li, Zhuohan; Zhuang, Siyuan; Sheng, Ying; Zheng, Lianmin; Yu, Cody Hao; Gonzalez, Joseph; Zhang, Hao; Stoica, Ion | Woosuk Kwon; Zhuo-Han Li; Siyuan Zhuang; Ying Sheng; Lian-Min Zheng; C. Yu; Joseph E. Gonzalez; Haotong Zhang; Ion Stoica | Woosuk Kwon; Z. Li; Siyuan Zhuang; Ying Sheng; L Zheng; Cody Hao Yu; Joseph E. Gonzalez; Hao Zhang; Ion Gabriel Stoica |
| venue | Proceedings of the 29th ACM Symposium on Operating Systems Principles (SOSP '23) | Proceedings of the 29th Symposium on Operating Systems Principles | Symposium on Operating Systems Principles | — |
| 页码 | 611--626 | 611-626 | — | 611--626 |
| DOI | 10.1145/3600006.3613165 | ✓ 解析成功 | 10.1145/3600006.3613165 | 10.1145/3600006.3613165 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `yu2022orca`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {Orca}: A Distributed Serving System for Transformer-Based Generative Models | — | — | Fast Distributed Inference Serving for Large Language Models |
| 年 | 2022 | — | — | 2023 |
| 作者 | Yu, Gyeong-In and Jeong, Joo Seong and Kim, Geon-Woo and Kim, Soojeong and Chun, Byung-Gon | — | — | Bingyang Wu; Yinmin Zhong; Zili Zhang; Liu, Shengyu; Liu, Fangyue; Sun, Yuanhang; Huang, Gang; Liu, Xuanzhe; Jin, Xin |
| venue | 16th USENIX Symposium on Operating Systems Design and Implementation (OSDI '22) | — | — | arXiv (Cornell University) |
| 页码 | 521--538 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2305.05920 |

**判定**：标题 ✗0.29 ｜ 年 ✗(2023) ｜ 作者 ✗ ｜ 页码 ?


## `yu2025pensieve`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Stateful Large Language Model Serving with {Pensieve} | Stateful Large Language Model Serving with Pensieve | Stateful Large Language Model Serving with Pensieve | Stateful Large Language Model Serving with Pensieve |
| 年 | 2025 | 2025 | 2023 | 2025 |
| 作者 | Yu, Lingfan and Lin, Jinkun and Li, Jinyang | Yu, Lingfan; Lin, Jinkun; Li, Jinyang | Lingfan Yu; Jinkun Lin; Jin-Yang Li | Lingfan Yu; Jinkun Lin; Jinyang Li |
| venue | Proceedings of the Twentieth European Conference on Computer Systems (EuroSys '25) | Proceedings of the Twentieth European Conference on Computer Systems | European Conference on Computer Systems | — |
| 页码 | 144--158 | 144-158 | — | 144--158 |
| DOI | 10.1145/3689031.3696086 | ✓ 解析成功 | 10.1145/3689031.3696086 | 10.1145/3689031.3696086 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `gao2024cachedattention`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Cost-Efficient Large Language Model Serving for Multi-turn Conversations with {CachedAttention} | — | — | Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention |
| 年 | 2024 | — | — | 2024 |
| 作者 | Gao, Bin and He, Zhuomin and Sharma, Puru and Kang, Qingxuan and Jevdjic, Djordje and Deng, Junbo and Yang, Xingkun and Yu, Zhou and Zuo, Pengfei | — | — | Bin Gao; Zhuomin He; Puru Sharma; Qingxuan Kang; Djordje Jevdjic; Junbo Deng; Xingkun Yang; Zhou Yu; P. B. Zuo |
| venue | 2024 USENIX Annual Technical Conference (USENIX ATC '24) | — | — | arXiv (Cornell University) |
| 页码 | 111--126 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2403.19708 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ 页码 ?


## `sun2024llumnix`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Llumnix: Dynamic Scheduling for Large Language Model Serving | — | Llumnix: Dynamic Scheduling for Large Language Model Serving | Llumnix: Dynamic Scheduling for Large Language Model Serving |
| 年 | 2024 | — | 2024 | 2024 |
| 作者 | Sun, Biao and Huang, Ziming and Zhao, Hanyu and Xiao, Wencong and Zhang, Xinyi and Li, Yong and Lin, Wei | — | Biao Sun; Ziming Huang; Hanyu Zhao; Wencong Xiao; Xinyi Zhang; Yong Li; Wei Lin | Biao Sun; Ziming Huang; Hanyu Zhao; Wencong Xiao; Xinyi Zhang; Yong Li; Wei Ting Lin |
| venue | 18th USENIX Symposium on Operating Systems Design and Implementation (OSDI '24) | — | USENIX Symposium on Operating Systems Design and Implementation | arXiv (Cornell University) |
| 页码 | 173--191 | — | — | — |
| DOI | None | 无 DOI 字段 | 10.48550/arXiv.2406.03243 | 10.48550/arxiv.2406.03243 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ 页码 ?


## `wu2026fastserve`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {FastServe}: Iteration-Level Preemptive Scheduling for Large Language Model Inference | — | — | Fast Distributed Inference Serving for Large Language Models |
| 年 | 2026 | — | — | 2023 |
| 作者 | Wu, Bingyang and Zhong, Yinmin and Zhang, Zili and Liu, Shengyu and Liu, Fangyue and Sun, Yuanhang and Huang, Gang and Liu, Xuanzhe and Jin, Xin | — | — | Bingyang Wu; Yinmin Zhong; Zili Zhang; Liu, Shengyu; Liu, Fangyue; Sun, Yuanhang; Huang, Gang; Liu, Xuanzhe; Jin, Xin |
| venue | 23rd USENIX Symposium on Networked Systems Design and Implementation (NSDI '26) | — | — | arXiv (Cornell University) |
| 页码 | 57--74 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2305.05920 |

**判定**：标题 ✗0.29 ｜ 年 ✗(2023) ｜ 作者 ~(3/9) ｜ 页码 ?


## `lin2024parrot`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {Parrot}: Efficient Serving of {LLM}-based Applications with Semantic Variable | — | — | Parrot: Efficient Serving of LLM-based Applications with Semantic Variable |
| 年 | 2024 | — | — | 2024 |
| 作者 | Lin, Chaofan and Han, Zhenhua and Zhang, Chengruidong and Yang, Yuqing and Yang, Fan and Chen, Chen and Qiu, Lili | — | — | Chaofan Lin; Han, Zhenhua; C. R. Zhang; Yuqing Yang; Yang, Fan; Chen, Chen; Qiu, Lili |
| venue | 18th USENIX Symposium on Operating Systems Design and Implementation (OSDI '24) | — | — | arXiv (Cornell University) |
| 页码 | 929--945 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2405.19888 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ~(4/7) ｜ 页码 ?


## `wang2026xperf`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Benchmarking {LLM} Serving Systems for Agentic {AI} Workloads with {XPerf} | — | — | Benchmarking LLM Serving Systems for Agentic AI Workloads with XPerf |
| 年 | 2026 | — | — | 2026 |
| 作者 | Wang, Michael and Yue, Yikang and Li, Shaobo and Zhou, Yirui Eric and Wang, Chen and Huang, Jian | — | — | Michael Wang; Yikang Yue; Shaobo Li; Yirui Eric Zhou; Chen Wang; Jian Huang |
| venue | None | — | — | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | 10.48550/arXiv.2608.20370 | ✗ 查不到 | — | 10.48550/arxiv.2608.20370 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ DOI ✗


## `wang2025kvcachewild`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {KVCache} Cache in the Wild: Characterizing and Optimizing {KVCache} Cache at a Large Cloud Provider | — | — | KVCache Cache in the Wild: Characterizing and Optimizing KVCache Cache at a Large Cloud Provider |
| 年 | 2025 | — | — | 2025 |
| 作者 | Wang, Jiahao and Han, Jinbo and Wei, Xingda and Shen, Sijie and Zhang, Dingyan and Fang, Chenguang and Chen, Rong and Yu, Wenyuan and Chen, Haibo | — | — | Jiahao Wang; Han, Jinbo; Xingda Wei; Sijie Shen; Zhang, Dingyan; Fang, Chenguang; Chen, Rong; Wenyuan Yu; Haibo Chen |
| venue | 2025 USENIX Annual Technical Conference (USENIX ATC '25) | — | — | arXiv (Cornell University) |
| 页码 | 465--482 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2506.02634 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ~(5/9) ｜ 页码 ?


## `qwen2coder`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Qwen2.5-Coder Technical Report | — | — | Qwen2.5-Coder Technical Report |
| 年 | 2024 | — | — | 2024 |
| 作者 | Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Lu, Keming and Dang, Kai and {Yang Fan} and {Yichang Zhang} and Yang, An and Men, Rui and Huang, Fei and {Bo Zheng} and {Yibo Miao} and Quan, Shanghaoran and {Yunlong Feng} and Ren, Xingzhang and Ren, Xuancheng and Zhou, Jingren and Lin, Junyang | — | — | Binyuan Hui; Jian Yang; Cui, Zeyu; Jiaxi Yang; Dayiheng Liu; Lei Zhang; Tianyu Liu; Jiajun Zhang; Bowen Yu; Lu, Keming; Kai Dang; Fan, Yang; Zhang, Yichang; Yang, An; Rui Men; Fei Huang; Zheng, Bo; Miao, Yibo; Quan, Shanghaoran; Feng, Yunlong; Xingzhang Ren; Xuancheng Ren; Jingren Zhou; Lin, Junyang |
| venue | None | — | — | arXiv (Cornell University) |
| 页码 | None | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2409.12186 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ~(10/24)


## `zerowsap`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {ZeroSwap}: Minimizing Swap Overhead for Real-Time Multi-{DNN} Inference via {SSD}-based {GPU} Memory Extension | ZeroSwap: Minimizing Swap Overhead for Real-Time Multi-DNN Inference via SSD-based GPU Memory Extension | ZeroSwap: Minimizing Swap Overhead for Real-Time Multi-DNN Inference via SSD-based GPU Memory Extension | ZeroSwap: Minimizing Swap Overhead for Real-Time Multi-DNN Inference via SSD-based GPU Memory Extension |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Kang, Woosung and Muzzini, Filippo and Brilli, Gianluca and Kim, Jong-Chan and Lee, Jinkyu and Chwa, Hoon Sung | Kang, Woosung; Muzzini, Filippo; Brilli, Gianluca; Kim, Jong-Chan; Lee, Jinkyu; Chwa, Hoon Sung | Woosung Kang; Filippo Muzzini; Gianluca Brilli; Jong-Chan Kim; Jinkyu Lee; H. Chwa | Woosung Kang; Filippo Muzzini; Gianluca Brilli; Jong-Chan Kim; Jinkyu Lee; Hoon Sung Chwa |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 234--246 | 234-246 | 234-246 | 234--246 |
| DOI | 10.1109/RTAS68450.2026.00030 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00030 | 10.1109/rtas68450.2026.00030 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `etm2`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {ETM}$^2$: Empowering Traditional Memory Bandwidth Regulation using {ETM} | ETM
                    <sup>2</sup>
                    : Empowering Traditional Memory Bandwidth Regulation using ETM | ETM2: Empowering Traditional Memory Bandwidth Regulation using ETM | ETM 2 : Empowering Traditional Memory Bandwidth Regulation using ETM |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Zuepke, Alexander and Pradhan, Ashutosh and Ottaviano, Daniele and Bastoni, Andrea and Caccamo, Marco | Zuepke, Alexander; Pradhan, Ashutosh; Ottaviano, Daniele; Bastoni, Andrea; Caccamo, Marco | Alexander Zuepke; Ashutosh Pradhan; Daniele Ottaviano; Andrea Bastoni; Marco Caccamo | Alexander Zuepke; Ashutosh Pradhan; Daniele Ottaviano; Andrea Bastoni; Marco Caccamo |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 180--193 | 180-193 | 180-193 | 180--193 |
| DOI | 10.1109/RTAS68450.2026.00026 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00026 | 10.1109/rtas68450.2026.00026 |

**判定**：标题 ~0.70 ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `perbank26`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Per-Bank Memory Bandwidth Regulation for Predictable and Performant Real-Time Systems | Per-Bank Memory Bandwidth Regulation for Predictable and Performant Real-Time Systems | Per-Bank Memory Bandwidth Regulation for Predictable and Performant Real-Time Systems | Per-Bank Memory Bandwidth Regulation for Predictable and Performant Real-Time Systems |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Sullivan, Connor Rudy and Mamandipoor, Amin and Strickler, Cole Ridge and Yun, Heechul | Sullivan, Connor Rudy; Mamandipoor, Amin; Strickler, Cole Ridge; Yun, Heechul | Connor Sullivan; Amin Mamandipoor; C. Strickler; H. Yun | Connor Rudy Sullivan; Amin Mamandipoor; Cole Ridge Strickler; Heechul Yun |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 167--179 | 167-179 | 167-179 | 167--179 |
| DOI | 10.1109/RTAS68450.2026.00025 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00025 | 10.1109/rtas68450.2026.00025 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `perbank24`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Per-Bank Bandwidth Regulation of Shared Last-Level Cache for Real-Time Systems | Per-Bank Bandwidth Regulation of Shared Last-Level Cache for Real-Time Systems | Per-Bank Bandwidth Regulation of Shared Last-Level Cache for Real-Time Systems | Per-Bank Bandwidth Regulation of Shared Last-Level Cache for Real-Time Systems |
| 年 | 2024 | 2024 | 2024 | 2024 |
| 作者 | Sullivan, Connor and Manley, Alex and Alian, Mohammad and Yun, Heechul | Sullivan, Connor; Manley, Alex; Alian, Mohammad; Yun, Heechul | Connor Sullivan; Alex Manley; Mohammad Alian; Heechul Yun | Craig Sullivan; Alex Manley; Mohammad Alian; Heechul Yun |
| venue | 2024 IEEE Real-Time Systems Symposium (RTSS) | 2024 IEEE Real-Time Systems Symposium (RTSS) | IEEE Real-Time Systems Symposium | — |
| 页码 | 336--348 | 336-348 | 336-348 | 336--348 |
| DOI | 10.1109/RTSS62706.2024.00036 | ✓ 解析成功 | 10.1109/RTSS62706.2024.00036 | 10.1109/rtss62706.2024.00036 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `memguard`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {MemGuard}: Memory bandwidth reservation system for efficient performance isolation in multi-core platforms | MemGuard: Memory bandwidth reservation system for efficient performance isolation in multi-core platforms | MemGuard: Memory bandwidth reservation system for efficient performance isolation in multi-core platforms | MemGuard: Memory bandwidth reservation system for efficient performance isolation in multi-core platforms |
| 年 | 2013 | 2013 | 2013 | 2013 |
| 作者 | Yun, Heechul and Yao, Gang and Pellizzoni, Rodolfo and Caccamo, Marco and Sha, Lui | Heechul Yun; Gang Yao; Pellizzoni, R.; Caccamo, M.; Lui Sha | H. Yun; Gang Yao; R. Pellizzoni; M. Caccamo; L. Sha | Heechul Yun; Gang Yao; Rodolfo Pellizzoni; Marco Caccamo; Lui Sha |
| venue | 2013 IEEE 19th Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2013 IEEE 19th Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 55--64 | 55-64 | 55-64 | 55--64 |
| DOI | 10.1109/RTAS.2013.6531079 | ✓ 解析成功 | 10.1109/RTAS.2013.6531079 | 10.1109/rtas.2013.6531079 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ~(3/5) ｜ 页码 ✓ ｜ DOI ✓


## `mempol`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {MemPol}: Policing Core Memory Bandwidth from Outside of the Cores | MemPol: Policing Core Memory Bandwidth from Outside of the Cores | — | MemPol: Policing Core Memory Bandwidth from Outside of the Cores |
| 年 | 2023 | 2023 | — | 2023 |
| 作者 | Zuepke, Alexander and Bastoni, Andrea and Chen, Weifan and Caccamo, Marco and Mancuso, Renato | Zuepke, Alexander; Bastoni, Andrea; Chen, Weifan; Caccamo, Marco; Mancuso, Renato | — | Alexander Zuepke; Andrea Bastoni; Weifan Chen; Marco Caccamo; Renato Mancuso |
| venue | 2023 IEEE 29th Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2023 IEEE 29th Real-Time and Embedded Technology and Applications Symposium (RTAS) | — | — |
| 页码 | 235--248 | 235-248 | — | 235--248 |
| DOI | 10.1109/RTAS58335.2023.00026 | ✓ 解析成功 | — | 10.1109/rtas58335.2023.00026 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `dynamo`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Analysis of Dynamic Memory Bandwidth Regulation in Multi-core Real-Time Systems | Analysis of Dynamic Memory Bandwidth Regulation in Multi-core Real-Time Systems | Analysis of Dynamic Memory Bandwidth Regulation in Multi-core Real-Time Systems | Analysis of Dynamic Memory Bandwidth Regulation in Multi-core Real-Time Systems |
| 年 | 2018 | 2018 | 2018 | 2018 |
| 作者 | Agrawal, Ankit and Mancuso, Renato and Pellizzoni, Rodolfo and Fohler, Gerhard | Agrawal, Ankit; Mancuso, Renato; Pellizzoni, Rodolfo; Fohler, Gerhard | Ankit Agrawal; R. Mancuso; R. Pellizzoni; G. Fohler | Ankit Kumar Agrawal; Renato Mancuso; Rodolfo Pellizzoni; Gerhard Fohler |
| venue | 2018 IEEE Real-Time Systems Symposium (RTSS) | 2018 IEEE Real-Time Systems Symposium (RTSS) | IEEE Real-Time Systems Symposium | — |
| 页码 | 230--241 | 230-241 | 230-241 | 230--241 |
| DOI | 10.1109/RTSS.2018.00040 | ✓ 解析成功 | 10.1109/RTSS.2018.00040 | 10.1109/rtss.2018.00040 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `yun2016`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Memory Bandwidth Management for Efficient Performance Isolation in Multi-Core Platforms | Memory Bandwidth Management for Efficient Performance Isolation in Multi-Core Platforms | Memory Bandwidth Management for Efficient Performance Isolation in Multi-Core Platforms | Memory Bandwidth Management for Efficient Performance Isolation in Multi-Core Platforms |
| 年 | 2016 | 2016 | 2016 | 2015 |
| 作者 | Yun, Heechul and Yao, Gang and Pellizzoni, Rodolfo and Caccamo, Marco and Sha, Lui | Yun, Heechul; Yao, Gang; Pellizzoni, Rodolfo; Caccamo, Marco; Sha, Lui | H. Yun; Gang Yao; R. Pellizzoni; M. Caccamo; L. Sha | Heechul Yun; Gang Yao; Rodolfo Pellizzoni; Marco Caccamo; Lui Sha |
| venue | IEEE Transactions on Computers | IEEE Transactions on Computers | IEEE transactions on computers | IEEE Transactions on Computers |
| 页码 | 562--576 | 562-576 | 562-576 | 562--576 |
| DOI | 10.1109/TC.2015.2425889 | ✓ 解析成功 | 10.1109/TC.2015.2425889 | 10.1109/tc.2015.2425889 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `rtswap`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {RT-Swap}: Addressing {GPU} Memory Bottlenecks for Real-Time Multi-{DNN} Inference | RT-Swap: Addressing GPU Memory Bottlenecks for Real-Time Multi-DNN Inference | — | RT-Swap: Addressing GPU Memory Bottlenecks for Real-Time Multi-DNN Inference |
| 年 | 2024 | 2024 | — | 2024 |
| 作者 | Kang, Woosung and Lee, Jinkyu and Lee, Youngmoon and Oh, Sangeun and Lee, Kilho and Chwa, Hoon Sung | Kang, Woosung; Lee, Jinkyu; Lee, Youngmoon; Oh, Sangeun; Lee, Kilho; Chwa, Hoon Sung | — | Woosung Kang; Jinkyu Lee; Youngmoon Lee; Sangeun Oh; Kilho Lee; Hoon Sung Chwa |
| venue | 2024 IEEE 30th Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2024 IEEE 30th Real-Time and Embedded Technology and Applications Symposium (RTAS) | — | — |
| 页码 | 373--385 | 373-385 | — | 373--385 |
| DOI | 10.1109/RTAS61025.2024.00037 | ✓ 解析成功 | — | 10.1109/rtas61025.2024.00037 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `xiang2019`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Pipelined Data-Parallel {CPU}/{GPU} Scheduling for Multi-{DNN} Real-Time Inference | Pipelined Data-Parallel CPU/GPU Scheduling for Multi-DNN Real-Time Inference | Pipelined Data-Parallel CPU/GPU Scheduling for Multi-DNN Real-Time Inference | Pipelined Data-Parallel CPU/GPU Scheduling for Multi-DNN Real-Time Inference |
| 年 | 2019 | 2019 | 2019 | 2019 |
| 作者 | Xiang, Yecheng and Kim, Hyoseung | Xiang, Yecheng; Kim, Hyoseung | Yecheng Xiang; Hyoseung Kim | Yecheng Xiang; Hyoseung Kim |
| venue | 2019 IEEE Real-Time Systems Symposium (RTSS) | 2019 IEEE Real-Time Systems Symposium (RTSS) | IEEE Real-Time Systems Symposium | — |
| 页码 | 392--405 | 392-405 | 392-405 | 392--405 |
| DOI | 10.1109/RTSS46320.2019.00042 | ✓ 解析成功 | 10.1109/RTSS46320.2019.00042 | 10.1109/rtss46320.2019.00042 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `tpdnndpu`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Time-Predictable Acceleration of Deep Neural Networks on {FPGA} {SoCs} with Multi-Core {DPUs} | Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs | Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs | Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Aromolo, Federico and Salamini, Niko and Del Granchio, Jacopo and Biondi, Alessandro and Marinoni, Mauro and Buttazzo, Giorgio | Aromolo, Federico; Salamini, Niko; Granchio, Jacopo Del; Biondi, Alessandro; Marinoni, Mauro; Buttazzo, Giorgio | Federico Aromolo; Niko Salamini; Jacopo Del Granchio; Alessandro Biondi; Mauro Marinoni; Giorgio C. Buttazzo | Federico Aromolo; Niko Salamini; Jacopo Del Granchio; Alessandro Biondi; Mauro Marinoni; Giorgio Buttazzo |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 275--288 | 275-288 | 275-288 | 275--288 |
| DOI | 10.1109/RTAS68450.2026.00033 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00033 | 10.1109/rtas68450.2026.00033 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `aiheat`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {AI} Inference in the Heat: Thermal-Aware Strict Partitioning for Configurable Real-Time Gang Tasks | AI Inference in the Heat: Thermal-Aware Strict Partitioning for Configurable Real-Time Gang Tasks | AI Inference in the Heat: Thermal-Aware Strict Partitioning for Configurable Real-Time Gang Tasks | AI Inference in the Heat: Thermal-Aware Strict Partitioning for Configurable Real-Time Gang Tasks |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Sun, Binqi and Li, Jinyang and Kloda, Tomasz and Abdelzaher, Tarek and Caccamo, Marco | Sun, Binqi; Li, Jinyang; Kloda, Tomasz; Abdelzaher, Tarek; Caccamo, Marco | Binqi Sun; Jinyang Li; T. Kloda; Tarek F. Abdelzaher; Marco Caccamo | B Sun; Jinyang Li; Tomasz Kloda; Tarek Abdelzaher; Marco Caccamo |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 247--260 | 247-260 | 247-260 | 247--260 |
| DOI | 10.1109/RTAS68450.2026.00031 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00031 | 10.1109/rtas68450.2026.00031 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `lmjamming`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Real-Time Language Model Jamming: A Case Study for Live Music Accompaniment Generation | Real-Time Language Model Jamming: A Case Study for Live Music Accompaniment Generation | — | Real-Time Language Model Jamming: A Case Study for Live Music Accompaniment Generation |
| 年 | 2026 | 2026 | — | 2026 |
| 作者 | Zheng, Bowen and Yang, Andrew H. and Ruan, Jiaqi and He, Jia and Li, Xinyue and Chen, Yuan-Hsin and Wang, Ziyu and Ma, Xiaosong | Zheng, Bowen; Yang, Andrew H.; Ruan, Jiaqi; He, Jia; Li, Xinyue; Chen, Yuan-Hsin; Wang, Ziyu; Ma, Xiaosong | — | Bowen Zheng; Andrew H. Yang; Jiaqi RUAN; Jia He; Xinyue Li; Yuan-Hsin Chen; Z Wang; Xiaosong Ma |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | — | — |
| 页码 | 261--274 | 261-274 | — | 261--274 |
| DOI | 10.1109/RTAS68450.2026.00032 | ✓ 解析成功 | — | 10.1109/rtas68450.2026.00032 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `fwagnostic`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Framework-Agnostic Model Inference for Intra-Thread Real-Time Tasks | Framework-Agnostic Model Inference for Intra-Thread Real-Time Tasks | Framework-Agnostic Model Inference for Intra-Thread Real-Time Tasks | Framework-Agnostic Model Inference for Intra-Thread Real-Time Tasks |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Ye, Bite and Markovi{\'c}, Filip and Brandenburg, Bj{\"o}rn B. | Ye, Bite; Marković, Filip; Brandenburg, Björn B. | Bite Ye; Filip Markovic; Björn B. Brandenburg | Bite Ye; Filip Marković; Björn B. Brandenburg |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 68--81 | 68-81 | 68-81 | 68--81 |
| DOI | 10.1109/RTAS68450.2026.00013 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00013 | 10.1109/rtas68450.2026.00013 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `schedconstraints`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Scheduling Constraints: A Universal {OS} Mechanism for Managing Shared Resources | Scheduling Constraints: A Universal OS Mechanism for Managing Shared Resources | Scheduling Constraints: A Universal OS Mechanism for Managing Shared Resources | Scheduling Constraints: A Universal OS Mechanism for Managing Shared Resources |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Lumme, Moritz and Roitzsch, Michael and Lackorzy{\'n}ski, Adam | Lumme, Moritz; Roitzsch, Michael; Lackorzyński, Adam | Moritz Lumme; Michael Roitzsch; A. Lackorzynski | Moritz Lumme; Michael Roitzsch; Adam Lackorzyński |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 400--413 | 400-413 | 400-413 | 400--413 |
| DOI | 10.1109/RTAS68450.2026.00042 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00042 | 10.1109/rtas68450.2026.00042 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `genprofiling`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Generative Profiling for Soft Real-Time Systems and its Applications to Resource Allocation | Generative Profiling for Soft Real-Time Systems and its Applications to Resource Allocation | Generative Profiling for Soft Real-Time Systems and its Applications to Resource Allocation | Generative Profiling for Soft Real-Time Systems and its Applications to Resource Allocation |
| 年 | 2026 | 2026 | 2026 | 2026 |
| 作者 | Bondar, Georgiy A. and Eisenklam, Abigail and Cai, Yifan and Gifford, Robert and Sial, Tushar and Phan, Linh Thi Xuan and Halder, Abhishek | Bondar, Georgiy A.; Eisenklam, Abigail; Cai, Yifan; Gifford, Robert; Sial, Tushar; Xuan Phan, Linh Thi; Halder, Abhishek | Georgiy A. Bondar; Abby Eisenklam; Yifan Cai; Robert Gifford; Tushar Sial; Linh Thi Xuan Phan; Abhishek Halder | Georgiy A. Bondar; Abigail Eisenklam; Yifan Cai; Robert Gifford; Tushar Sial; Linh Thi Xuan Phan; Abhishek Halder |
| venue | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | 2026 IEEE 32nd Real-Time and Embedded Technology and Applications Symposium (RTAS) | IEEE Real Time Technology and Applications Symposium | — |
| 页码 | 289--302 | 289-302 | 289-302 | 289--302 |
| DOI | 10.1109/RTAS68450.2026.00034 | ✓ 解析成功 | 10.1109/RTAS68450.2026.00034 | 10.1109/rtas68450.2026.00034 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `wilhelm2008`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | The worst-case execution-time problem---overview of methods and survey of tools | The worst-case execution-time problem—overview of methods and survey of tools | The worst-case execution-time problem—overview of methods and survey of tools | The worst-case execution-time problem—overview of methods and survey of tools |
| 年 | 2008 | 2008 | 2008 | 2008 |
| 作者 | Wilhelm, Reinhard and Engblom, Jakob and Ermedahl, Andreas and Holsti, Niklas and Thesing, Stephan and Whalley, David and Bernat, Guillem and Ferdinand, Christian and Heckmann, Reinhold and Mitra, Tulika and Mueller, Frank and Puaut, Isabelle and Puschner, Peter and Staschulat, Jan and Stenstr{\"o}m, Per | Wilhelm, Reinhard; Engblom, Jakob; Ermedahl, Andreas; Holsti, Niklas; Thesing, Stephan; Whalley, David; Bernat, Guillem; Ferdinand, Christian; Heckmann, Reinhold; Mitra, Tulika; Mueller, Frank; Puaut, Isabelle; Puschner, Peter; Staschulat, Jan; Stenström, Per | R. Wilhelm; Jakob Engblom; Andreas Ermedahl; N. Holsti; Stephan Thesing; D. Whalley; G. Bernat; C. Ferdinand; R. Heckmann; T. Mitra; F. Mueller; I. Puaut; P. Puschner; Jan Staschulat; P. Stenstrom | Reinhard Wilhelm; Jakob Engblom; Andreas Ermedahl; Niklas Holsti; Stephan Thesing; David B. Whalley; Guillem Bernat; Christian Ferdinand; Reinhold Heckmann; Tulika Mitra; Frank Mueller; Isabelle Puaut; Peter P. Puschner; Jan Staschulat; Per Stenström |
| venue | ACM Transactions on Embedded Computing Systems | ACM Transactions on Embedded Computing Systems | TECS | ACM Transactions on Embedded Computing Systems |
| 页码 | 1--53 | 1-53 | 36:1-36:53 | 1--53 |
| DOI | 10.1145/1347375.1347389 | ✓ 解析成功 | 10.1145/1347375.1347389 | 10.1145/1347375.1347389 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `flashattention`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {FlashAttention}: Fast and Memory-Efficient Exact Attention with {IO}-Awareness | — | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness |
| 年 | 2022 | — | 2022 | 2022 |
| 作者 | Dao, Tri and Fu, Dan and Ermon, Stefano and Rudra, Atri and R{\'e}, Christopher | — | Tri Dao; Daniel Y. Fu; S. Ermon; A. Rudra; Christopher Ré | Tri Dao; Dan Fu; Stefano Ermon; Atri Rudra; Christopher Ré |
| venue | Advances in Neural Information Processing Systems 35 (NeurIPS 2022) | — | Neural Information Processing Systems | — |
| 页码 | 16344--16359 | — | — | 16344--16359 |
| DOI | None | 无 DOI 字段 | 10.52202/068431-1189 | 10.52202/068431-1189 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ 页码 ✓


## `flexgen`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {FlexGen}: High-Throughput Generative Inference of Large Language Models with a Single {GPU} | — | — | FlexGen: High-Throughput Generative Inference of Large Language Models with a Single GPU |
| 年 | 2023 | — | — | 2023 |
| 作者 | Sheng, Ying and Zheng, Lianmin and Yuan, Binhang and Li, Zhuohan and Ryabinin, Max and Chen, Beidi and Liang, Percy and R{\'e}, Christopher and Stoica, Ion and Zhang, Ce | — | — | Ying Sheng; Lianmin Zheng; Binhang Yuan; Zhuohan Li; Max Ryabinin; Daniel Y. Fu; Zhiqiang Xie; Beidi Chen; Clark Barrett; Joseph E. Gonzalez; Percy Liang; Christopher Ré; Ion Gabriel Stoica; Ce Zhang |
| venue | Proceedings of the 40th International Conference on Machine Learning (ICML 2023) | — | — | arXiv (Cornell University) |
| 页码 | 31094--31116 | — | — | — |
| DOI | None | 无 DOI 字段 | — | 10.48550/arxiv.2303.06865 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓⊂(10v14) ｜ 页码 ?


## `h2o`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | {H2O}: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models | — | H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models | H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models |
| 年 | 2023 | — | 2023 | 2023 |
| 作者 | Zhang, Zhenyu and Sheng, Ying and Zhou, Tianyi and Chen, Tianlong and Zheng, Lianmin and Cai, Ruisi and Song, Zhao and Tian, Yuandong and R{\'e}, Christopher and Barrett, Clark and Wang, Zhangyang and Chen, Beidi | — | Clark W. Barrett; Ruisi Cai; Beidi Chen; Tian-Long Chen; Christopher Ré; Ying Sheng; Zhao Song; Yuan-Dong Tian; Zhangyang Wang; Zhenyu (Allen) Zhang; Lian-Min Zheng; Tianyi Zhou | Zhenyu Zhang; Ying Sheng; Tianyi Zhou; Tianlong Chen; Lianmin Zheng; Ruisi Cai; Zhao Song; Yuandong Tian; Christopher Ré; Clark Barrett; Zhangyang "atlas" Wang; Beidi Chen |
| venue | Advances in Neural Information Processing Systems 36 (NeurIPS 2023) | — | Neural Information Processing Systems | — |
| 页码 | 34661--34710 | — | — | 34661--34710 |
| DOI | None | 无 DOI 字段 | 10.48550/arXiv.2306.14048 | 10.52202/075280-1506 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ 页码 ✓


## `scissorhands`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Scissorhands: Exploiting the Persistence of Importance Hypothesis for {LLM} {KV} Cache Compression at Test Time | — | — | Scissorhands: Exploiting the Persistence of Importance Hypothesis for LLM KV Cache Compression at Test Time |
| 年 | 2023 | — | — | 2023 |
| 作者 | Liu, Zichang and Desai, Aditya and Liao, Fangshuo and Wang, Weitao and Xie, Victor and Xu, Zhaozhuo and Kyrillidis, Anastasios and Shrivastava, Anshumali | — | — | Zichang Liu; Aditya Desai; Fangshuo Liao; Weitao Wang; Victor Xie; Zhaozhuo Xu; Anastasios Kyrillidis; Anshumali Shrivastava |
| venue | Advances in Neural Information Processing Systems 36 (NeurIPS 2023) | — | — | — |
| 页码 | 52342--52364 | — | — | 52342--52364 |
| DOI | None | 无 DOI 字段 | — | 10.52202/075280-2279 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✓ ｜ 页码 ✓


## `splitwise`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Splitwise: Efficient Generative {LLM} Inference Using Phase Splitting | Splitwise: Efficient Generative LLM Inference Using Phase Splitting | Splitwise: Efficient Generative LLM Inference Using Phase Splitting | Splitwise: Efficient Generative LLM Inference Using Phase Splitting |
| 年 | 2024 | 2024 | 2023 | 2024 |
| 作者 | Patel, Pratyush and Choukse, Esha and Zhang, Chaojie and Shah, Aashaka and Goiri, {\'I}{\~n}igo and Maleki, Saeed and Bianchini, Ricardo | Patel, Pratyush; Choukse, Esha; Zhang, Chaojie; Shah, Aashaka; Goiri, Íñigo; Maleki, Saeed; Bianchini, Ricardo | P. Patel; Esha Choukse; Chaojie Zhang; Aashaka Shah; Í. Goiri; Saeed Maleki; Ricardo Bianchini | Pratyush Patel; Esha Choukse; Chaojie Zhang; Aashaka Shah; Íñigo Goiri; Saeed Maleki; Ricardo Bianchini |
| venue | 2024 ACM/IEEE 51st Annual International Symposium on Computer Architecture (ISCA) | 2024 ACM/IEEE 51st Annual International Symposium on Computer Architecture (ISCA) | International Symposium on Computer Architecture | — |
| 页码 | 118--132 | 118-132 | 118-132 | 118--132 |
| DOI | 10.1109/ISCA59077.2024.00019 | ✓ 解析成功 | 10.1109/ISCA59077.2024.00019 | 10.1109/isca59077.2024.00019 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `little1961`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | A Proof for the Queuing Formula: $L = \lambda W$ | A Proof for the Queuing Formula:
                    <i>L</i>
                    = λ
                    <i>W</i> | A Proof for the Queuing Formula: L = λW | A Proof for the Queuing Formula: L = λ W |
| 年 | 1961 | 1961 | 1961 | 1961 |
| 作者 | Little, John D. C. | Little, John D. C. | J. Little | John D. C. Little |
| venue | Operations Research | Operations Research | Operations Research | Operations Research |
| 页码 | 383--387 | 383-387 | 383-387 | 383--387 |
| DOI | 10.1287/opre.9.3.383 | ✓ 解析成功 | 10.1287/OPRE.9.3.383 | 10.1287/opre.9.3.383 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `denning1978`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | The Operational Analysis of Queueing Network Models | The Operational Analysis of Queueing Network Models | The Operational Analysis of Queueing Network Models | The Operational Analysis of Queueing Network Models |
| 年 | 1978 | 1978 | 1978 | 1978 |
| 作者 | Denning, Peter J. and Buzen, Jeffrey P. | Denning, Peter J.; Buzen, Jeffrey P. | P. Denning; J. Buzen | Peter J. Denning; Jeffrey P. Buzen |
| venue | ACM Computing Surveys | ACM Computing Surveys | CSUR | ACM Computing Surveys |
| 页码 | 225--261 | 225-261 | 225-261 | 225--261 |
| DOI | 10.1145/356733.356735 | ✓ 解析成功 | 10.1145/356733.356735 | 10.1145/356733.356735 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `jacobson1988`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Congestion Avoidance and Control | Congestion avoidance and control | Congestion avoidance and control | Congestion avoidance and control |
| 年 | 1988 | 1988 | 1988 | 1988 |
| 作者 | Jacobson, Van | Jacobson, V. | V. Jacobson | Van L. Jacobson |
| venue | Symposium Proceedings on Communications Architectures and Protocols (SIGCOMM '88) | Symposium proceedings on Communications architectures and protocols | Conference on Applications, Technologies, Architectures, and Protocols for Computer Communication | — |
| 页码 | 314--329 | 314-329 | 314-329 | 314--329 |
| DOI | 10.1145/52324.52356 | ✓ 解析成功 | 10.1145/52324.52356 | 10.1145/52324.52356 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓


## `liu1973`

| 字段 | 论文里声称 | Crossref | Semantic Scholar | OpenAlex |
|---|---|---|---|---|
| 标题 | Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment | Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment | Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment | Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment |
| 年 | 1973 | 1973 | 1989 | 1973 |
| 作者 | Liu, C. L. and Layland, James W. | Liu, C. L.; Layland, James W. | C.-L. Liu; J. Layland | C. L. Liu; J. W. Layland |
| venue | Journal of the ACM | Journal of the ACM | JACM | Journal of the ACM |
| 页码 | 46--61 | 46-61 | 46-61 | 46--61 |
| DOI | 10.1145/321738.321743 | ✓ 解析成功 | 10.1145/321738.321743 | 10.1145/321738.321743 |

**判定**：标题 ✓ ｜ 年 ✓ ｜ 作者 ✗ ｜ 页码 ✓ ｜ DOI ✓

