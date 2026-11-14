"""LoRA SFT of Gemma 4 (default 12B-it) on the verified secure-coding set, one H200, no vLLM.

Prompt = the chat template WITH the generation prompt (Gemma 4 adds an empty thought channel there,
so training sees exactly what generation sees); target = assistant answer + "<turn|>\n".
Loss only on the target. LoRA on the text model's attention and MLP projections only (not vision
or audio towers).

  python cluster/sft.py --model google/gemma-4-12B-it --train data/secpy_train.jsonl \
      --val data/secpy_val.jsonl --out runs/sft12b
"""
import argparse, json, os

import torch
import transformers
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments

TARGETS = r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"
END = "<turn|>\n"


def load_model(path):
    cls = getattr(transformers, "AutoModelForMultimodalLM", None) or transformers.AutoModelForImageTextToText
    return cls.from_pretrained(path, dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")


def encode(tok, row, max_len):
    msgs = row["messages"]
    prompt = tok.apply_chat_template(msgs[:-1], add_generation_prompt=True, tokenize=False)
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    a_ids = tok(msgs[-1]["content"] + END, add_special_tokens=False)["input_ids"]
    ids = p_ids + a_ids
    if len(ids) > max_len:
        return None
    return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": [-100] * len(p_ids) + a_ids}


def load(tok, path, max_len):
    rows = [encode(tok, json.loads(l), max_len) for l in open(path)]
    kept = [r for r in rows if r]
    print(f"{path}: {len(kept)}/{len(rows)} examples (dropped {len(rows) - len(kept)} over {max_len} tokens)", flush=True)
    return Dataset.from_list(kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-12B-it")
    ap.add_argument("--train", default="data/secpy_train.jsonl")
    ap.add_argument("--val", default="data/secpy_val.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max_len", type=int, default=4096)
    ap.add_argument("--grad_accum", type=int, default=16)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    train, val = load(tok, a.train, a.max_len), load(tok, a.val, a.max_len)
    print("example prompt tail:", repr(tok.decode(train[0]["input_ids"][:200])[-120:]), flush=True)

    model = load_model(a.model)
    model.config.use_cache = False
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05,
                                             target_modules=TARGETS, task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    n_lora = sum(1 for n, _ in model.named_modules() if n.endswith(".lora_A"))
    print("LoRA modules:", n_lora, flush=True)
    assert n_lora > 0, "LoRA matched no layers; check TARGETS against model.named_modules()"

    args = TrainingArguments(
        output_dir=a.out, num_train_epochs=a.epochs, learning_rate=a.lr, lr_scheduler_type="cosine",
        warmup_ratio=0.03, per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=a.grad_accum, bf16=True, gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False}, logging_steps=5,
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=1, report_to="none",
        remove_unused_columns=False, dataloader_num_workers=2)
    Trainer(model=model, args=args, train_dataset=train, eval_dataset=val,
            data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100)).train()
    model.save_pretrained(os.path.join(a.out, "adapter"))
    tok.save_pretrained(os.path.join(a.out, "adapter"))
    print("adapter written to", os.path.join(a.out, "adapter"), flush=True)


if __name__ == "__main__":
    main()
