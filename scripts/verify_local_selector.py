"""Actual free CPU model through a loopback compatible HTTP extract-selection adapter.

A smoke test of interoperability/fail-closed evidence validation, not answer quality.
Model weights stay in the ignored cache. No provider key, fee or hosting is used.
"""

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from time import perf_counter

from releaselens.db import create_local_schema, database
from releaselens.fixtures import fixture
from releaselens.generation import CompatibleGenerator
from releaselens.ingestion import ingest
from releaselens.retrieval import HashEmbedder
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, validate_citations

ROOT = Path(__file__).resolve().parents[1]
MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"


def main():
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(2)
    start = perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, trust_remote_code=False, use_safetensors=True
    ).eval()
    load_ms = (perf_counter() - start) * 1000
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.send_error(404)
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            inputs = tokenizer.apply_chat_template(
                body["messages"], add_generation_prompt=True, return_tensors="pt", return_dict=True
            )
            started = perf_counter()
            with torch.inference_mode():
                output = model.generate(
                    **inputs,
                    max_new_tokens=min(body["max_tokens"], 192),
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            prompt_tokens = inputs["input_ids"].shape[-1]
            content = tokenizer.decode(output[0][prompt_tokens:], skip_special_tokens=True)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": output.shape[-1] - prompt_tokens,
                "total_tokens": output.shape[-1],
            }
            calls.append(
                {
                    "latency_ms": (perf_counter() - started) * 1000,
                    "usage": usage,
                    "raw_output": content,
                    "server_max_new_tokens": 192,
                }
            )
            payload = json.dumps(
                {"choices": [{"message": {"content": content}}], "usage": usage}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    records = []
    try:
        with factory.begin() as session:
            encoder, principal = HashEmbedder(), Principal("local-smoke", "admin")
            ingest(
                session,
                principal,
                fixture("selector", "1.0", "policy", "The request_timeout default is 30 seconds."),
                encoder,
            )
            session.info["generator"] = CompatibleGenerator(
                f"http://127.0.0.1:{server.server_port}/v1", MODEL
            )
            for question, expected in [
                ("What is the request_timeout default?", False),
                (
                    "Does request_timeout guarantee every database transaction is serializable?",
                    True,
                ),
            ]:
                started = perf_counter()
                payload = ask(
                    session,
                    principal,
                    AskRequest(project="selector", release="1.0", question=question, save=False),
                    encoder,
                )
                elapsed = (perf_counter() - started) * 1000
                validate_citations(session, principal, payload)
                records.append(
                    {
                        "question": question,
                        "expected_abstention_ai_proposal": expected,
                        "observed_abstention": bool(payload.abstention_reason),
                        "reason": payload.abstention_reason,
                        "answer": payload.answer,
                        "citation_count": len(payload.passages),
                        "exact_citation_validation_passed": True,
                        "end_to_end_ms": elapsed,
                        "metadata": payload.metadata,
                        "human_correctness": None,
                    }
                )
    finally:
        server.shutdown()
        server.server_close()
        engine.dispose()
    model_files = {}
    cache = Path(os.getenv("HF_HOME", ROOT / ".model-cache"))
    for folder in cache.glob(
        "hub/models--HuggingFaceTB--SmolLM2-135M-Instruct/snapshots/" + REVISION
    ):
        for file in folder.rglob("*"):
            if file.is_file():
                model_files[str(file.relative_to(folder))] = {
                    "bytes": file.stat().st_size,
                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                }
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": f"{MODEL}@{REVISION}",
        "license": "Apache-2.0 per upstream model metadata",
        "device": "cpu",
        "torch_threads": torch.get_num_threads(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "load_ms": load_ms,
        "actual_model_http_requests": len(calls),
        "calls": calls,
        "records": records,
        "model_files": model_files,
        "provider_cost_usd": 0,
        "electricity_network_cost_usd": None,
        "scope": "Real 135M CPU model, loopback compatible HTTP adapter, two synthetic smoke probes; no human answer correctness or synthesis evaluation",
        "limits": [
            "Tiny model may fail JSON/extract selection; failures are recorded, never relabeled successes.",
            "Server caps generation at 192 new tokens for this smoke; no constrained grammar.",
            "Exact citations do not establish relevance or entailment.",
        ],
    }
    (ROOT / "evaluation/local-selector-v3.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {k: record[k] for k in ("model", "actual_model_http_requests", "load_ms", "records")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
