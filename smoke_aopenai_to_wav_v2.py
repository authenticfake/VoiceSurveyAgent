import asyncio
import base64
import json
import websockets

from app.dialogue.llm.openai_adapter import OpenAIRealtimeSession

STREAM_SID = "MS_MOCK_123"

# --- Twilio WS MOCK ---
async def twilio_ws_mock(websocket):
    print("[MOCK] Twilio WS connected")
    async for msg in websocket:
        evt = json.loads(msg)
        assert evt["event"] == "media"
        assert evt["streamSid"] == STREAM_SID
        payload = evt["media"]["payload"]
        raw = base64.b64decode(payload)
        print(f"[MOCK] media received: {len(raw)} bytes")

# --- Bridge logic ---
async def bridge(openai, twilio_ws):
    for _ in range(200):
        evt = await openai.recv_event()
        etype = evt.get("type")
        print("[OPENAI]", etype)

        if etype == "response.output_audio.delta":
            delta = evt.get("delta")
            if not delta:
                continue

            frame = {
                "event": "media",
                "streamSid": STREAM_SID,
                "media": {
                    "payload": delta
                }
            }
            await twilio_ws.send(json.dumps(frame))
            print("[BRIDGE] media frame sent")
            break

        if etype in ("response.error", "error"):
            print("ERROR:", evt)
            break

# --- Main ---
async def main():
    # start mock server
    server = await websockets.serve(twilio_ws_mock, "localhost", 8765)
    print("[MOCK] listening on ws://localhost:8765")

    # connect to mock as client (simula backend → Twilio)
    async with websockets.connect("ws://localhost:8765") as twilio_ws:
        s = OpenAIRealtimeSession.from_env(
            instructions="Parla in italiano. Sii brevissimo."
        )
        await s.connect()
        await s.start_greeting(text_hint="Di solo: ciao.")

        await bridge(s, twilio_ws)

        await s.close()

    server.close()
    await server.wait_closed()

asyncio.run(main())
