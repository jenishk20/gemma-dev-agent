"""LoRA fine-tuning of a competition Gemma 4 model on teacher conversations (training/build_sft.py output).

Base weights: the same W4A16 QAT checkpoint Kaggle serves, unpacked to bf16 for training
(compressed-tensors run_compressed=False), so the adapter is trained on the weights it will run on.

Text: each conversation goes through the model's own chat template the way vLLM sends it
(tool-call arguments as dicts, past thoughts in `reasoning`/`reasoning_content`, thinking on).
Loss: only on the assistant turns (thoughts + tool calls + replies), never on the system prompt,
the task text or tool results. A turn whose text can't be located exactly in the rendered conversation
is left out of the loss and counted.

    python training/train_lora.py --data sft.jsonl --model $GDA_ROOT/models/gemma-4-e4b-it-qat-w4a16-ct --show 1
    python training/train_lora.py --data sft.jsonl --model ... --check-load
    python training/train_lora.py --data sft.jsonl --model ... --out adapters/main_lora
"""
import argparse
import json
import math
import random
import time
from copy import deepcopy
from pathlib import Path

# Text decoder only (never the vision/audio towers), for both multimodal (…language_model.layers…) and
# text-only (model.layers…) checkpoints. PEFT full-matches this against module names.
PROJ = r"(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
TARGETS = rf"(.*\.language_model\..*\.{PROJ}|model\.layers\.\d+\..*\.{PROJ})"


def for_template(messages):
    """Messages as vLLM hands them to the chat template."""
    out = []
    for m in deepcopy(messages):
        if m["role"] == "assistant":
            if m.get("content") is None:
                m["content"] = ""
            if m.get("reasoning_content"):
                m["reasoning"] = m["reasoning_content"]     # adk_submission's patch sends both
            for tc in m.get("tool_calls") or []:
                args = tc["function"].get("arguments")
                if isinstance(args, str):
                    try:
                        tc["function"]["arguments"] = json.loads(args)
                    except json.JSONDecodeError:
                        pass
        out.append(m)
    return out


def render(tok, messages, tools, gen):
    return tok.apply_chat_template(messages, tools=tools or None, tokenize=False, add_generation_prompt=gen,
                                   enable_thinking=True)


def assistant_spans(tok, ex):
    """Full text + character spans of every assistant turn that sits exactly where generation would put it."""
    msgs = for_template(ex["messages"])
    full = render(tok, msgs, ex["tools"], False)
    spans, missed = [], 0
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        before = render(tok, msgs[:i], ex["tools"], True)
        upto = render(tok, msgs[: i + 1], ex["tools"], False)
        if full.startswith(before) and full.startswith(upto) and len(upto) > len(before):
            spans.append((len(before), len(upto)))
        else:
            missed += 1
    return full, spans, missed


def encode(tok, ex, max_len):
    full, spans, missed = assistant_spans(tok, ex)
    enc = tok(full, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    labels = [-100] * len(ids)
    for j, (a, b) in enumerate(offs):
        if any(s <= a and b <= e for s, e in spans):
            labels[j] = ids[j]
    if len(ids) > max_len:
        return None, missed
    return {"input_ids": ids, "labels": labels}, missed


def load_tokenizer(path):
    from transformers import AutoProcessor, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    if not getattr(tok, "chat_template", None):
        tok.chat_template = AutoProcessor.from_pretrained(path).chat_template
    return tok


def load_model(path):
    import torch
    import transformers
    from transformers import AutoConfig
    cfg = AutoConfig.from_pretrained(path)
    arch = getattr(transformers, cfg.architectures[0])
    kw = {"dtype": torch.bfloat16, "device_map": {"": 0}, "attn_implementation": "sdpa"}
    if getattr(cfg, "quantization_config", None):
        from transformers import CompressedTensorsConfig
        kw["quantization_config"] = CompressedTensorsConfig(run_compressed=False)   # unpack INT4 -> bf16
    return arch.from_pretrained(path, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="adapters/main_lora")
    ap.add_argument("--show", type=int, default=0, help="print N rendered examples and stop (no GPU)")
    ap.add_argument("--check-load", action="store_true", help="load model + LoRA, print a summary, stop")
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--alpha", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--accum", type=int, default=8, help="conversations per optimizer step")
    ap.add_argument("--max-len", type=int, default=32768)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    tok = load_tokenizer(args.model)
    examples = [json.loads(l) for l in open(args.data) if l.strip()]
    print(f"{len(examples)} conversations from {args.data}", flush=True)

    if args.show:
        for ex in examples[: args.show]:
            full, spans, missed = assistant_spans(tok, ex)
            n_tok = len(tok(full, add_special_tokens=False)["input_ids"])
            trained = sum(b - a for a, b in spans)
            print(f"\n===== {ex['instance_id']} ({ex['run']}): {n_tok} tokens, {len(spans)} assistant turns trained, "
                  f"{missed} not located, {trained / max(1, len(full)):.0%} of characters trained")
            print("----- start of text:\n" + full[:1500])
            if spans:
                a, b = spans[0]
                print(f"----- first trained turn (chars {a}-{b}):\n" + full[a:b][:1500])
                a, b = spans[-1]
                print(f"----- last trained turn (chars {a}-{b}):\n" + full[a:b][:1500])
            print("----- end of text:\n" + full[-600:])
        return

    import torch
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    data, missed_total, too_long = [], 0, 0
    for ex in examples:
        enc, missed = encode(tok, ex, args.max_len)
        missed_total += missed
        if enc is None:
            too_long += 1
        elif any(x != -100 for x in enc["labels"]):
            data.append(enc)
    n_lab = sum(sum(x != -100 for x in d["labels"]) for d in data)
    print(f"{len(data)} usable, {too_long} longer than {args.max_len} tokens, {missed_total} turns not located; "
          f"{sum(len(d['input_ids']) for d in data)} tokens, {n_lab} trained", flush=True)

    model = load_model(args.model)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, bias="none",
                                             target_modules=TARGETS, task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    names = [n for n, p in model.named_parameters() if p.requires_grad]
    print("first LoRA weights:", names[:4], flush=True)
    model.train()                                              # gradient checkpointing only runs in train mode
    if args.check_load:                                        # one real loss + backward on the longest example
        d = max(data, key=lambda d: len(d["input_ids"]))
        ids, lab = torch.tensor([d["input_ids"]], device="cuda"), torch.tensor(d["labels"], device="cuda")
        keep = (lab[1:] != -100).nonzero().squeeze(1)
        loss = torch.nn.functional.cross_entropy(model(input_ids=ids, logits_to_keep=keep).logits[0].float(), lab[keep + 1])
        loss.backward()
        print(f"check ok: {len(d['input_ids'])} tokens, loss {loss.item():.3f}, "
              f"peak GPU memory {torch.cuda.max_memory_allocated() / 1e9:.1f} GB", flush=True)
        return

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0, betas=(0.9, 0.99))
    total = max(1, math.ceil(len(data) * args.epochs / args.accum))
    warm = max(1, total // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))
    order = []
    while len(order) < total * args.accum:
        chunk = list(range(len(data)))
        random.shuffle(chunk)
        order += chunk
    order = order[: total * args.accum]

    model.train()
    t0, step = time.time(), 0
    for k in range(0, len(order), args.accum):
        batch = [data[i] for i in order[k: k + args.accum]]
        n_batch = sum(sum(x != -100 for x in d["labels"]) for d in batch)   # token-weighted mean over the batch
        loss_sum = 0.0
        for d in batch:
            ids = torch.tensor([d["input_ids"]], device="cuda")
            lab = torch.tensor(d["labels"], device="cuda")
            keep = (lab[1:] != -100).nonzero().squeeze(1)       # positions whose NEXT token is trained
            out = model(input_ids=ids, logits_to_keep=keep)
            logits = out.logits[0].float()
            loss = torch.nn.functional.cross_entropy(logits, lab[keep + 1], reduction="sum") / n_batch
            loss.backward()
            loss_sum += loss.item()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        print(f"step {step}/{total} loss {loss_sum:.4f} lr {sched.get_last_lr()[0]:.2e} "
              f"{(time.time() - t0) / 60:.1f} min", flush=True)

    out = Path(args.out)
    model.save_pretrained(out)
    cfg = json.loads((out / "adapter_config.json").read_text())
    cfg["base_model_name_or_path"] = Path(args.model).name                # no local paths in the submission
    (out / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
    print(f"saved {out}: " + ", ".join(f"{p.name} {p.stat().st_size / 1e6:.0f} MB" for p in sorted(out.iterdir())))


if __name__ == "__main__":
    main()
