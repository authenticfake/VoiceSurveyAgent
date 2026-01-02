import asyncio
import base64
import wave
from app.dialogue.llm.openai_adapter import OpenAIRealtimeSession

OUT_WAV = "openai_adapter_smoke.wav"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1

async def main():
    s = OpenAIRealtimeSession.from_env(
        instructions="Parla in italiano. Sii brevissimo."
    )
    await s.connect()
    await s.start_greeting(text_hint="Di solo: ciao. Poi taci.")

    audio = bytearray()

    for i in range(200):
        evt = await s.recv_event()
        etype = evt.get("type")
        print(i, etype)

        if etype == "response.output_audio.delta":
            delta = evt.get("delta")
            if delta:
                audio.extend(base64.b64decode(delta))

        if etype in (
            "response.output_audio.done",
            "response.completed",
            "response.audio.done",
        ):
            break

        if etype in ("response.error", "error"):
            print("ERROR:", evt)
            break

    await s.close()

    print("Audio bytes:", len(audio))
    assert len(audio) > 0, "AUDIO VUOTO"

    with wave.open(OUT_WAV, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio)

    print("WAV scritto:", OUT_WAV)

asyncio.run(main())
