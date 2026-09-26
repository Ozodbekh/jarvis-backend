# JARVIS uchun o'rnatilgan narsalar

Egasi uchun ro'yxat: JARVIS ishlashi uchun kompyuterga nima o'rnatilgan, qayerda turibdi, qancha joy egallaydi va
qanday o'chiriladi. Hajmlar 2026-09-24 da o'lchangan. Tizimga (`sudo apt`) hech narsa o'rnatilmagan.

## Qisqacha

| Nima | Qayerda | Hajmi | JARVIS uchun kerakmi |
|---|---|---|---|
| Python kutubxonalari | `jarvis-backend/.venv/` | 2.5 GB | ha |
| Ovoz modellari (whisper, MMS) | `~/.cache/huggingface/` | 7.3 GB jami | qisman — pastda |
| Piper ovozlari (rus, ingliz) | `jarvis-backend/data/voices/` | 121 MB | ha |
| O'zbekcha whisper (konvertatsiya qilingan) | `jarvis-backend/data/models/` | 980 MB | `whisper-small-uz` — ha; `navai-…` — yo'q |
| Sinov ma'lumotlari (FLEURS o'zbekcha) | `jarvis-backend/data/eval/` | 623 MB | yo'q, faqat sinov uchun |
| Vault — JARVIS xotirasi, sizning eslatmalaringiz | `~/jarvis-vault/` | 80 KB | ha, **sizning ma'lumotingiz** |
| Sinov uchun vaqtinchalik muhit | `/tmp/claude-1000/…/scratchpad/` | 1.7 GB | yo'q, kompyuter o'chsa o'zi o'chadi |
| `uv` yuklab olgan paketlar keshi | `~/.cache/uv/` | 7.1 GB | yo'q, lekin boshqa loyihalaringiz ham ishlatadi |

## 1. Python kutubxonalari — `.venv/` (2.5 GB)

`pyproject.toml` da yozilgan. Eng kattalari:

| Paket | Hajmi | Nima uchun |
|---|---|---|
| `torch` (faqat CPU) | 742 MB | o'zbekcha ovoz (MMS) va modellarni konvertatsiya qilish |
| `PySide6` | 649 MB | desktop oyna, mikrofon va karnay |
| `claude-agent-sdk` | 225 MB | Claude Code — ichida o'zining Claude Code dasturi bor |
| `transformers` | 61 MB | MMS o'zbekcha ovoz |
| `faster-whisper` + `ctranslate2` | ~140 MB | ovozni matnga o'girish (STT) |
| `openwakeword` + `onnxruntime` | ~75 MB | "Hey Jarvis" so'zini eshitish; model paket ichida (11 MB) |
| `piper-tts` | 46 MB | rus va ingliz ovozi |
| `fastapi`, `pydantic`, `structlog` va boshqalar | qolgani | backend |
| `ruff`, `mypy`, `pytest`, `import-linter` | kichik | faqat dasturchi uchun tekshiruvlar |

O'chirish: `rm -rf ~/PycharmProjects/jarvis-backend/.venv` — qayta kerak bo'lsa `uv sync` hammasini qaytaradi.

## 2. Hugging Face modellari — `~/.cache/huggingface/` (7.3 GB)

Birinchi ishlatilganda avtomatik yuklangan.

| Model | Hajmi | Kerakmi |
|---|---|---|
| `Systran/faster-whisper-small` | 464 MB | **ha** — hozirgi STT (`VOICE_STT_MODEL=small`) |
| `facebook/mms-tts-uzb-script_cyrillic` | 139 MB | **ha** — o'zbekcha ovoz |
| `Systran/faster-whisper-medium` | 1.5 GB | yo'q — faqat solishtirish uchun yuklangan |
| `mobiuslabsgmbh/faster-whisper-large-v3-turbo` | 1.6 GB | yo'q — faqat solishtirish uchun yuklangan |
| `navai-uz/whisper-medium-uzbek` (asl nusxa) | 2.9 GB | yo'q — `data/models/` ga konvertatsiya qilingan nusxasi bor |
| `OvozifyLabs/whisper-small-uz-v1` (asl nusxa) | 925 MB | yo'q — `data/models/whisper-small-uz` ga konvertatsiya qilingan; o'chirilsa va u papka ham yo'q bo'lsa, qayta yuklanadi |

Bitta modelni o'chirish, masalan:
`rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-medium`

Hammasini o'chirish: `rm -rf ~/.cache/huggingface` — JARVIS keyingi ishga tushishda keraklilarini qayta yuklaydi
(taxminan 600 MB).

## 3. `jarvis-backend/data/` — git'ga kirmaydi

| Papka / fayl | Hajmi | Nima |
|---|---|---|
| `voices/` | 121 MB | Piper: `ru_RU-irina-medium`, `en_US-amy-medium`. O'chirilsa qayta yuklanadi |
| `models/whisper-small-uz/` | 239 MB | **ishlatiladi** — o'zbekcha STT (`OvozifyLabs/whisper-small-uz-v1`). O'chirilsa, keyingi ishga tushishda qayta konvertatsiya qilinadi |
| `models/navai-uz_whisper-medium-uzbek/` | 741 MB | kerak emas — solishtirishda yutqazdi, o'chirsa bo'ladi |
| `eval/fleurs_uz_test.parquet` | 623 MB | Google FLEURS o'zbekcha test yozuvlari — modellarni o'lchash uchun |
| `state.json` | kichik | Claude sessiyasi ID'si. O'chirilsa yangi suhbat boshlanadi, xotira yo'qolmaydi |
| `backend.log` | kichik | desktop oyna ishga tushirgan backend'ning logi |

Sinov narsalarini o'chirish:
`rm -rf ~/PycharmProjects/jarvis-backend/data/eval ~/PycharmProjects/jarvis-backend/data/models/navai-uz_whisper-medium-uzbek`
`rm -rf ~/.cache/huggingface/hub/models--navai-uz--whisper-medium-uzbek ~/.cache/huggingface/hub/models--Systran--faster-whisper-medium ~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo`
— bular birgalikda taxminan 7.4 GB bo'shatadi, JARVIS'ga ta'sir qilmaydi.

## 4. Vault — `~/jarvis-vault/`

JARVIS'ning xotirasi: siz aytgan eslatmalar, metrikalar, rejalar. **O'chirsangiz, JARVIS eslab qolgan hamma narsa
yo'qoladi.** Qayta bo'sh vault: `make vault`.

## 5. Tizimdagi boshqa narsalar

- `~/.cache/uv/` (7.1 GB) — `uv` ning umumiy keshi, boshqa Python loyihalaringiz ham ishlatadi. Tozalash:
  `uv cache clean` (keyingi `uv sync` sekinroq bo'ladi).
- Python 3.14 (`~/.local/share/uv/python/`) — loyiha shu versiyada ishlaydi, boshqa loyihalaringiz ham ishlatadi.
- `libportaudio2` o'rnatilmagan — kerak bo'lmadi, desktop Qt'ning o'z audio'sidan foydalanadi.

## Yangi kompyuterda ishga tushirish

```
git clone <repo> jarvis-backend && cd jarvis-backend
cp .env.example .env
uv sync                  # Python kutubxonalari (~2.5 GB)
make vault               # ~/jarvis-vault
make jarvis              # oyna; birinchi ishga tushishda modellar yuklanadi (~1 GB), o'zbekcha STT konvertatsiya qilinadi
```

Claude Code'ga shu kompyuterda kirilgan bo'lishi kerak (`claude` bilan login). `data/` va `~/jarvis-vault`
git'ga kirmaydi — eslatmalarni ko'chirmoqchi bo'lsangiz, `~/jarvis-vault` ni qo'lda ko'chiring.

## JARVIS'ni butunlay o'chirish

```
rm -rf ~/PycharmProjects/jarvis-backend      # kod, .venv, data/
rm -rf ~/.cache/huggingface                  # modellar (boshqa loyiha ishlatmasa)
rm -rf ~/jarvis-vault                        # xotira — faqat kerak bo'lmasa
```

Bu fayl yangi narsa o'rnatilganda yangilanadi.
