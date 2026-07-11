# Retrieval Benchmark

> **⚠️ Benchmark on tiny corpus (30 chunks from 15 documents).  
> 100% retrieval rate is expected — index is too small for meaningful recall measurement.**

---

## Benchmark Setup

| Parameter | Value |
|-----------|-------|
| Index size | 30 chunks |
| Test queries | 8 |
| Top-K | 5 |
| Similarity threshold | 0.5 |
| Embedding model | all-MiniLM-L6-v2 |

---

## Results

| Query | Top-K Retrieved | Mean Score | Latency | Notes |
|-------|----------------|------------|---------|-------|
| "What climate risks affect Karnataka?" | 5/5 | 0.712 | 2ms | Government + Risk docs |
| "Explain monsoon patterns in India" | 5/5 | 0.689 | 1ms | IMD + Research docs |
| "How does ISRO monitor climate?" | 5/5 | 0.701 | 2ms | ISRO docs |
| "What are the effects of +2°C warming?" | 5/5 | 0.654 | 1ms | Research docs |
| "Flood risk assessment methodology" | 5/5 | 0.623 | 2ms | Risk docs |
| "Government policies on climate adaptation" | 5/5 | 0.645 | 1ms | Government docs |
| "Temperature trends in South India" | 5/5 | 0.638 | 2ms | Research + IMD docs |
| "Drought management strategies" | 5/5 | 0.631 | 1ms | Risk + Government docs |

| Aggregate Metric | Value |
|------------------|-------|
| Mean retrieval score | 0.659 |
| 100% retrieval rate | 8/8 queries |
| Mean latency | 1.5ms |
| P95 latency | 2ms |

---

## Category Coverage

| Category | Queries Matched | Notes |
|----------|----------------|-------|
| Government | 3 | Policy + Drought |
| ISRO | 1 | Climate monitoring |
| IMD | 2 | Monsoon + Temperature |
| Research | 3 | Warming + Trends + Monsoon |
| Risk | 3 | Flood + Drought + Risk assessment |

---

## Limitations

1. **100% retrieval rate is meaningless.** 30 chunks is too small for any chunk to be irrelevant. A random query would still retrieve something.
2. **Mean score of 0.659 is low.** On a 30-chunk index with 384-dim embeddings, scores should be higher if the corpus was well-matched. Indicates poor document-to-query alignment.
3. **No negative queries.** All 8 queries target content known to exist in the corpus.
4. **No out-of-domain queries.** No measurement of false positive rate.
5. **No A/B comparison.** No baseline against different chunk sizes, overlap, or embedding models.
6. **Not reproducible.** Random seed not specified for document order.
