import sys
import os
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from utils import config
# Add IndicTrans2 inference path
sys.path.append(os.path.join(os.path.dirname(__file__), "IndicTrans2/inference"))
from IndicTransToolkit import IndicProcessor

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
ip = IndicProcessor(inference=True)
CHUNK_SIZE = 32 if DEVICE == "cuda" else 8

# Language pairs for both directions
language_pairs = [
    ("eng_Latn", "hin_Deva"),
    ("eng_Latn", "mar_Deva"),
    ("eng_Latn", "guj_Gujr"),
    ("eng_Latn", "tam_Taml"),
    ("eng_Latn", "tel_Telu"),
    ("eng_Latn", "ben_Beng"),
    # Reverse directions
    ("hin_Deva", "eng_Latn"),
    ("mar_Deva", "eng_Latn"),
    ("guj_Gujr", "eng_Latn"),
    ("tam_Taml", "eng_Latn"),
    ("tel_Telu", "eng_Latn"),
    ("ben_Beng", "eng_Latn"),
]
model_map = {}

try:
    if config.QDRANT_HOST == '10.0.120.223':
        base_model_path = "/home/neosoft/workspace/llm/LLM_union/ai4bharat"
    else:
        base_model_path = "/hrbot/ai4bharat"
    model_map = {
        "eng_Latn->indic": os.path.join(base_model_path, "indictrans2-en-indic-dist-200M/snapshots/d383838cff138425e745261bf8ffe5aaf7cb69c1"),
        "indic->eng_Latn": os.path.join(base_model_path, "indictrans2-indic-en-dist-200M/snapshots/44e264ffa07dc1cae043e0fd864cab035068bf78"),
    }

    for direction, path in model_map.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model path not found for {direction}: {path}")

    print(" Translation models found and paths set.")

except Exception as e:
    model_map = {}  # Optional: Clear the map if failed
    print(f"❌ Error loading translation model paths: {e}")

loaded_models = {}

def get_model_tokenizer(direction):
    if direction not in loaded_models:
        model_name = model_map[direction]
        print(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name,local_files_only=True, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            local_files_only=True,
            trust_remote_code=True,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            attn_implementation="flash_attention_2" if DEVICE == "cuda" else None,
        ).to(DEVICE)
        loaded_models[direction] = (tokenizer, model)
    return loaded_models[direction]
MODEL_TOKENIZER = {
    "eng_Latn->indic": get_model_tokenizer("eng_Latn->indic"),
    "indic->eng_Latn": get_model_tokenizer("indic->eng_Latn")
}
def translate_batch(sentences, src_lang, tgt_lang):
    direction = "eng_Latn->indic" if src_lang == "eng_Latn" else "indic->eng_Latn"
    
    tokenizer, model = MODEL_TOKENIZER[direction]

    batch = ip.preprocess_batch([sentences], src_lang=src_lang, tgt_lang=tgt_lang)
    inputs = tokenizer(batch, truncation=True, padding="longest", return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model.generate(**inputs, use_cache=True, min_length=0, max_length=256, num_beams=1)

    with tokenizer.as_target_tokenizer():
        decoded = tokenizer.batch_decode(outputs.detach().cpu().tolist(), skip_special_tokens=True)

    translation = ip.postprocess_batch(decoded, lang=tgt_lang)
    print(translation[0],44444444444444444444)
    return translation[0]
# # Process all pairs
# for src_lang, tgt_lang in language_pairs:
#     direction = "eng_Latn->indic" if src_lang == "eng_Latn" else "indic->eng_Latn"
#     tokenizer, model = get_model_tokenizer(direction)

#     print(f"\n🔄 {src_lang} ➝ {tgt_lang}")
#     sentences = example_sentences[src_lang]
#     translations = translate_batch(sentences, src_lang, tgt_lang, tokenizer, model)

#     for src, tgt in zip(sentences, translations):
#         print(f"{src_lang}: {src}")
#         print(f"{tgt_lang}: {tgt}")
