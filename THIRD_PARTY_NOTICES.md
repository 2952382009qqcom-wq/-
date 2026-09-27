# Third-party components and design references

This file records the open-source components used by the competition build of
Mingjian (ChatLaw). The application code in this repository remains original
unless a section below explicitly says otherwise. Full dependency license texts
and transitive dependency notices should be generated again before the final
competition submission.

## Runtime components

| Component | Version | Purpose | License | Source |
| --- | --- | --- | --- | --- |
| RapidOCR | 3.9.2 | Offline Chinese/English OCR for photos and scanned documents | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| PaddleOCR-derived ONNX models bundled by RapidOCR | bundled with RapidOCR | OCR detection, orientation and recognition | RapidOCR's README states that model copyright belongs to Baidu; confirm and retain the exact upstream model terms before redistribution | https://github.com/RapidAI/RapidOCR#license |
| ONNX Runtime | 1.30.0 | CPU inference backend for RapidOCR | MIT | https://github.com/microsoft/onnxruntime |
| pypdfium2 / PDFium | 5.13.0 | Render scanned PDF pages for OCR | Apache-2.0 / BSD-style upstream notices | https://github.com/pypdfium2-team/pypdfium2 |
| pypdf | 6.19.0 | Extract existing PDF text layers | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| Pillow | 12.3.0 | Safe image loading and normalization | HPND | https://github.com/python-pillow/Pillow |
| Flask-SocketIO | 5.5.1 | Authenticated real-time direct messaging with REST fallback | MIT | https://github.com/miguelgrinberg/Flask-SocketIO |
| Flask-Limiter | 3.12 | Abuse-resistant request rate limiting | MIT | https://github.com/alisaifee/flask-limiter |
| Flask-Migrate / Alembic | 4.1.0 | Additive relational schema migrations | MIT | https://github.com/miguelgrinberg/Flask-Migrate |
| Redis client | 6.4.0 | Optional shared Socket.IO and rate-limit backend | MIT | https://github.com/redis/redis-py |
| Meilisearch Python SDK | 0.37.0 | Optional full-text community and case search | MIT | https://github.com/meilisearch/meilisearch-python |
| chinese-law-corpus case compilation | 2026-09-09 commit `ce5e48b4be0cccae3445dfeb9f0d2a94588208fe` | Structured source for 271 bundled Supreme People's Court guiding cases and 222 Gazette judgments; every record retains its primary official URL | CC0-1.0 | https://github.com/lttxzmj/chinese-law-corpus |

RapidOCR's engineering code is Apache-2.0, while its README separately states
that OCR-model copyright belongs to Baidu. Before redistributing the Python
environment, a server image or an Android package containing those model files,
capture the exact packaged-model origin and applicable license/notice text and
ship those notices with the artifact.

The underlying statutes and judicial documents are public official texts. The
third-party corpus contributes only compilation and structuring work, which its
maintainer dedicates to the public domain under CC0-1.0. MingJian does not copy
site chrome, logos, QR codes or unrelated photographs from court pages.

## Design references (not vendored)

The following projects were reviewed for architecture and test ideas. Their
source code is not copied into this repository:

- Microsoft Presidio (MIT): extensible PII recognizers and anonymization
  pipeline - https://github.com/data-privacy-stack/presidio
- FlagEmbedding (MIT): dense retrieval and reranking architecture -
  https://github.com/FlagOpen/FlagEmbedding
- Lawgent (MIT, with its upstream NOTICE requirements): citation guards and
  grounded legal-answer workflow - https://github.com/WenzhuoXu/lawgent
- LlamaIndex (MIT): history-aware question condensation and chat/RAG design -
  https://github.com/run-llama/llama_index
- RAGFlow (Apache-2.0): source-bounded citation prompting and retrieval answer
  verification design - https://github.com/infiniflow/ragflow
- Legal-RAG (license metadata must be rechecked before code reuse): statute-level
  chunking and hybrid retrieval evaluation - https://github.com/Fan-Luo/Legal-RAG
- FlaskBB (BSD-3-Clause): blueprint/service/model organization, moderation and
  nested-discussion architecture - https://github.com/flaskbb/flaskbb
- implicit (MIT): future collaborative-filtering upgrade path after sufficient
  interaction data exists; no runtime code is currently vendored -
  https://github.com/benfred/implicit
- LeCaRD / LeCaRDv2 (MIT): legal case retrieval evaluation references only;
  their corpora are not bundled and are not used as production case sources -
  https://github.com/myx666/LeCaRD

These references are listed for transparent provenance. Any future source-level
reuse must add the exact commit, copied files, modifications and required
license/NOTICE text here before release.
