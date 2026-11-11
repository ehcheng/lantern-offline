# AI model files

These are the brains that llamafile loads. On their own they do nothing; the program that runs them is `tools/llamafile/` (instructions there). Two are chat models for the Ask page, one is a search model the box itself uses.

| File | Size | What it is | Use it when |
|---|---|---|---|
| `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | 2.0 GB | Llama 3.2, 3 billion parameters, 4-bit. Meta, 2024. | The laptop has 8 GB of RAM, or you want fast answers. Fine for plain questions and rewording text. |
| `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | 4.9 GB | Llama 3.1, 8 billion parameters, 4-bit. Meta, 2024. | The laptop has 16 GB or more. Slower, better at longer reasoning. Start here on a modern MacBook. |
| `nomic-embed-text-v1.5.f16.gguf` | 274 MB | Nomic text embedding model. Apache 2.0. | Never by hand. The box runs it to power "similar pages" in search and the Ask page's retrieval. Do not delete it. |

All three were checked 2026-09-16 (GGUF file header present, sizes match the publisher's) and the 3B model was loaded and answered a question on a Mac 2026-09-30.

## The rule about medical advice

These models were not trained for this library and know nothing about what is in it beyond what the Ask page hands them. They can state a wrong drug dose with complete confidence. That is why the Ask page refuses to give doses and points to the printed drug guides instead. Treat anything they say about medicine, wild plants or canning as a starting point for looking it up on the shelf, never as the answer.

## Licenses

The two Llama models are under the Llama 3.1 and Llama 3.2 Community License, in `LICENSE-llama-3.1.txt` and `LICENSE-llama-3.2.txt` here. Keep those files with any copy you make. Both licenses require the notice "Built with Llama" on anything built from them. Nomic embed is Apache 2.0.

Newer models: the Ask page works with any GGUF chat model llamafile can load. `REFRESH.md` on the front page covers swapping one in and re-checking the file.
