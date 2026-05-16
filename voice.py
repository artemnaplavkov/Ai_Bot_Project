import whisper
import sounddevice as sd
import numpy as np
import keyboard
import time

model = whisper.load_model("base")

def record_until_key_release(trigger_key='ctrl', fs=16000):
    print(f"Зажмите и держите '{trigger_key.upper()}' для записи...")
    keyboard.wait(trigger_key)
    print("Запись началась")
    
    audio_buffer = []
    stream = sd.InputStream(samplerate=fs, channels=1, dtype=np.float32)
    stream.start()
    
    while keyboard.is_pressed(trigger_key):
        data, _ = stream.read(int(fs * 0.1))
        audio_buffer.append(data.copy())
        time.sleep(0.05)
    
    stream.stop()
    stream.close()
    print("Запись завершена.")
    
    if audio_buffer:
        full_audio = np.concatenate(audio_buffer, axis=0)
        full_audio = full_audio.flatten()
        return full_audio, fs
    else:
        return np.array([]), fs

def listen():
    audio, fs = record_until_key_release(trigger_key='ctrl')
    if len(audio) == 0:
        print("Ничего не записано.")
        return ""
    
    print("Распознаю...")
    result = model.transcribe(audio, language="ru", fp16=False)
    text = result["text"].strip()
    print(f"Вы сказали: {text}")
    return text