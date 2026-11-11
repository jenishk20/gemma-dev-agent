"""Generate BaxBench answers with plain transformers (no vLLM) on one H200, base or + LoRA adapter.

  python cluster/gen.py --model google/gemma-4-12B-it --prompts data/baxbench_prompts.jsonl \
      --out gens/base12b.jsonl [--adapter runs/sft12b/adapter] [--n 5 --temperature 0.4]
Writes {"scenario", "env", "sample", "response", "new_tokens"} rows; resumes if --out exists.
Same sampling as the OpenRouter runs: temperature 0.4, n samples per prompt, thinking off.
"""
import argparse, json, os, time

import torch
import transformers
from transformers import AutoTokenizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-12B-it")
    ap.add_argument("--adapter")
    ap.add_argument("--prompts", default="data/baxbench_prompts.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.4)
    ap.add_argument("--max_new_tokens", type=int, default=6144)
    ap.add_argument("--prompts_per_batch", type=int, default=6)  # x n sequences per batch
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    cls = getattr(transformers, "AutoModelForMultimodalLM", None) or transformers.AutoModelForImageTextToText
    model = cls.from_pretrained(a.model, dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
        model = model.merge_and_unload()
    model.eval()

    rows = [json.loads(l) for l in open(a.prompts)]
    done = set()
    if os.path.exists(a.out):
        done = {(r["scenario"], r["env"]) for r in map(json.loads, open(a.out))}
    todo = [r for r in rows if (r["scenario"], r["env"]) not in done]
    print(f"{len(todo)} prompts to generate ({len(done)} already in {a.out})", flush=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    end_ids = [tok.eos_token_id] + [i for i in [tok.convert_tokens_to_ids("<turn|>")] if isinstance(i, int) and i >= 0]

    t0 = time.time()
    with open(a.out, "a") as f:
        for b in range(0, len(todo), a.prompts_per_batch):
            batch = todo[b:b + a.prompts_per_batch]
            texts = [tok.apply_chat_template([{"role": "system", "content": r["system"]},
                                              {"role": "user", "content": r["user"]}],
                                             add_generation_prompt=True, tokenize=False) for r in batch]
            enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
            with torch.no_grad():
                out = model.generate(**enc, do_sample=True, temperature=a.temperature, top_p=1.0,
                                     max_new_tokens=a.max_new_tokens, num_return_sequences=a.n,
                                     eos_token_id=end_ids, pad_token_id=tok.pad_token_id)
            gen = out[:, enc["input_ids"].shape[1]:]
            for k, seq in enumerate(gen):
                r = batch[k // a.n]
                text = tok.decode(seq, skip_special_tokens=True)
                n_tok = int((seq != tok.pad_token_id).sum())
                f.write(json.dumps({"scenario": r["scenario"], "env": r["env"], "sample": k % a.n,
                                    "response": text, "new_tokens": n_tok}) + "\n")
            f.flush()
            print(f"  {min(b + a.prompts_per_batch, len(todo))}/{len(todo)} prompts ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
