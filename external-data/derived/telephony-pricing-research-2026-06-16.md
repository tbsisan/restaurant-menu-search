# Telephony / PSTN termination pricing for phone-order calls

_Date: 2026-06-16. Sources captured via Jina Reader mirrors of provider pricing pages._

## Context

Phone-order calls need:
1. **PSTN termination** (calling the restaurant's regular phone number)
2. **STT** (Speech-to-Text on the recorded call)
3. **LLM** (extracting the order from the transcript)
4. **TTS** (Text-to-Speech for any response back to the restaurant)

This file focuses on **item 1: PSTN termination pricing**. Updated per-call cost estimates at the end include all four components.

## Twilio baseline (for comparison)

| Product | Rate |
|---|---|
| Twilio PSTN outbound (US) | ~$0.0145/min |
| Twilio SIP trunk | ~$0.0045/min + termination |
| Twilio Programmable Voice (inbound) | $0.0085/min |

A 3-minute call via Twilio PSTN outbound ≈ **$0.0435**.

## Cheaper alternatives — pricing captured

| Provider | Product / route | Outbound rate/min | Inbound | Notes |
|---|---|---|---|---|
| **Plivo** | Local Calls | **$0.0115** | $0.0055 | Cheaper than Twilio; also has SIP |
| **Plivo** | Toll-Free Calls | **$0.0060** | $0.0180 | Cheapest captured outbound |
| **Plivo** | Browser SDK & SIP Calls | **$0.0033** | $0.0033 | Cheapest option IF you can use SIP/Browser SDK |
| **Bandwidth** | US local outbound | **~$0.0100** | $0.0055 | Direct-to-carrier; needs volume commit for best rates |
| **Bandwidth** | SMS outbound | $0.0040/message | — | Also does messaging |
| **Vonage** | Voice API (PSTN leg) | **~$0.01446** | — | Similar to Twilio; not cheaper |
| **Telnyx** | Voice API | Not captured | — | Page had no pricing numbers |
| **VoIP.ms** | Rates page | Not captured | — | Fetch failed / empty |

## Key pricing models

| Model | How it works | Best for |
|---|---|---|
| **PSTN API (Twilio-style)** | Per-minute outbound + per-minute inbound | Simple integration; highest per-minute cost |
| **SIP trunking (Plivo SIP, Bandwidth, VoIP.ms)** | Per-minute channel usage; bring your own PBX (FreeSWITCH, Asterisk, etc.) | 30–50% cheaper than PSTN API |
| **Browser SDK / WebRTC (Plivo Browser SDK)** | Call from browser/agent dashboard; uses SIP rates | Cheapest if staff/agent is browser-based |
| **Direct carrier / wholesale** | Contract + commit; $0.003–$0.006/min | High volume (10K+ mins/mo) |

## Cheapest realistic options for our use case

**Option A: Plivo Browser SDK or SIP — $0.0033/min**
- If the agent placing the call is a browser/WebRTC client (i.e., our system initiates from a browser or server-side SIP), this is the cheapest captured rate.
- 3-minute call = **$0.0099**.

**Option B: Plivo Toll-Free outbound — $0.0060/min**
- If the restaurant has a toll-free number and we call it, or we use a toll-free caller-ID.
- 3-minute call = **$0.018**.

**Option C: Plivo Local outbound — $0.0115/min**
- Calling regular local numbers.
- 3-minute call = **$0.0345**.

**Option D: Bandwidth direct-to-carrier — ~$0.0100/min (negotiable)**
- Needs commit; better rates at volume.
- 3-minute call = **~$0.030**.

**Option E: Self-hosted FreeSWITCH + cheap DID provider — ~$0.005–$0.010/min**
- Bring your own VoIP termination (e.g., VoIP.ms, Anveo wholesale).
- High ops overhead; not recommended initially.

## Updated per-call cost estimate (3-minute call, 100–1,000 words)

| Component | Cheapest realistic | Mid-grade | Premium |
|---|---|---|---|
| **Telephony (Plivo Browser SDK)** | $0.010 | $0.030 (Plivo local) | $0.050 (Twilio) |
| **STT (Whisper API)** | $0.018 | $0.018 (Whisper) | $0.045 (AssemblyAI) |
| **LLM (cheap model)** | $0.0005 | $0.008 (mid model) | $0.025 (Opus) |
| **TTS (Polly Standard)** | $0.008 | $0.048 (Polly Neural) | $0.60 (ElevenLabs) |
| **Total/call** | **~$0.037** | **~$0.104** | **~$0.720** |

**With Plivo SIP/Browser SDK + Whisper + cheap LLM + Polly Standard: ~$0.04/call.**

## What we should actually do

1. **Start with Plivo** (not Twilio) — $0.0115/min local outbound is ~20% cheaper than Twilio; SIP/Browser SDK at $0.0033/min is ~75% cheaper.
2. **Use SIP trunking** if we're doing any volume — the per-minute rate drops substantially.
3. **Self-host Whisper** for STT (free variable cost; only CPU/GPU time).
4. **Self-host piper/espeak** for TTS (free).
5. At 1,000 calls/mo, the difference between Twilio and Plivo SIP is roughly:
   - Twilio: ~$43/mo (telephony only)
   - Plivo SIP: ~$10/mo (telephony only)
   - **Savings: ~$33/mo at 1K calls**.

## Action

- [ ] Sign up for Plivo account and test $10 free credit
- [ ] Compare Plivo SIP trunking rates vs. their PSTN API rates
- [ ] Test Whisper (local) vs. Whisper API for STT cost
- [ ] Get VoIP.ms pricing (fetch failed; try direct navigation)
- [ ] Decide: PSTN API (simple) vs. SIP trunking (cheaper, more ops)

## Source pages captured

- Plivo pricing: https://plivo.com/pricing/ (captured via Jina Reader)
- Bandwidth pricing: https://www.bandwidth.com/pricing/ (partial)
- Vonage API pricing: https://www.vonage.com/communications-apis/pricing (partial)
- Telnyx pricing: https://www.telnyx.com/pricing (no numbers captured)
