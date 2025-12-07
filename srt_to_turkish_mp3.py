import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pysrt
from pydub import AudioSegment
from openai import OpenAI

# ---------- AYARLAR ----------
# OPENAI_API_KEY ortam değişkenine kaydedilmiş olmalı
client = OpenAI()

# OpenAI TTS için model ve sesler
TTS_MODEL = "gpt-4o-mini-tts"

VOICE_MAP = {
    "Kadın": "alloy",   # Kadın benzeri bir ton varsayıyoruz
    "Erkek": "verse"    # Erkek benzeri bir ton varsayıyoruz (örnek isim)
}
# -----------------------------


def srt_to_segments(srt_path):
    """
    SRT dosyasını okuyup [(start_ms, end_ms, text), ...] listesi döndürür.
    """
    subs = pysrt.open(srt_path, encoding='utf-8')
    segments = []
    for sub in subs:
        start = sub.start
        end = sub.end
        start_ms = (start.hours * 3600 + start.minutes * 60 + start.seconds) * 1000 + int(start.milliseconds)
        end_ms = (end.hours * 3600 + end.minutes * 60 + end.seconds) * 1000 + int(end.milliseconds)
        text = sub.text.replace('\n', ' ')
        segments.append((start_ms, end_ms, text))
    return segments


def tts_to_wav_bytes(text, voice):
    """
    Verilen metni OpenAI TTS ile WAV byte'ına çevirir.
    """
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=text,
        format="wav"
    )
    return response  # bu zaten bytes benzeri bir içerik döndürüyor


def build_full_timeline(segments, voice):
    """
    Zaman damgalarına sadık kalarak tek bir AudioSegment oluştur.
    """
    if not segments:
        return None

    # Toplam süreyi belirle (son altyazının bitişine göre)
    total_duration_ms = segments[-1][1] + 1000  # sonrasına 1 sn pay
    full_audio = AudioSegment.silent(duration=total_duration_ms)

    for i, (start_ms, end_ms, text) in enumerate(segments, start=1):
        if not text.strip():
            continue

        print(f"[{i}/{len(segments)}] TTS: {text[:60]}...")
        wav_bytes = tts_to_wav_bytes(text, voice)

        # Bytes'tan pydub AudioSegment'e çevir
        segment_audio = AudioSegment.from_file(
            io.BytesIO(wav_bytes),
            format="wav"
        )

        # Segmentin süresi altyazı aralığından uzunsa gerekirse hafif kısaltılabilir
        seg_duration = len(segment_audio)
        target_duration = end_ms - start_ms
        if seg_duration > target_duration and target_duration > 500:
            segment_audio = segment_audio[:target_duration]

        # Sessiz tam zaman çizelgesine yerleştir
        full_audio = full_audio.overlay(segment_audio, position=start_ms)

    return full_audio


def process_file(srt_path, voice_label):
    """
    Seçilen SRT dosyasını, seçilen sesle aynı klasöre MP3 olarak yazar.
    """
    voice = VOICE_MAP.get(voice_label, "alloy")

    segments = srt_to_segments(srt_path)
    if not segments:
        raise RuntimeError("SRT içinde altyazı bulunamadı.")

    full_audio = build_full_timeline(segments, voice)
    if full_audio is None:
        raise RuntimeError("Ses üretilemedi.")

    folder = os.path.dirname(srt_path)
    base = os.path.splitext(os.path.basename(srt_path))[0]
    output_path = os.path.join(folder, f"{base}.mp3")

    print(f"MP3 kaydediliyor: {output_path}")
    full_audio.export(output_path, format="mp3")
    return output_path


# ---------- GUI KISMI ----------
import io  # AudioSegment.from_file için lazım

def select_file():
    path = filedialog.askopenfilename(
        title="SRT dosyası seç",
        filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
    )
    if path:
        srt_path_var.set(path)


def start_conversion():
    srt_path = srt_path_var.get()
    voice_label = voice_var.get()

    if not srt_path or not os.path.isfile(srt_path):
        messagebox.showerror("Hata", "Lütfen geçerli bir SRT dosyası seçin.")
        return

    try:
        root.config(cursor="wait")
        root.update()

        output_path = process_file(srt_path, voice_label)
        messagebox.showinfo("Tamamlandı", f"Ses dosyası oluşturuldu:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{e}")
    finally:
        root.config(cursor="")
        root.update()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("SRT → Türkçe TTS (MP3)")

    # Dosya seç
    frm = ttk.Frame(root, padding=10)
    frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="SRT dosyası:").grid(row=0, column=0, sticky="w")
    srt_path_var = tk.StringVar()
    entry = ttk.Entry(frm, textvariable=srt_path_var, width=60)
    entry.grid(row=0, column=1, padx=5)
    ttk.Button(frm, text="Seç...", command=select_file).grid(row=0, column=2)

    # Ses seçimi
    ttk.Label(frm, text="Ses:").grid(row=1, column=0, sticky="w", pady=(10, 0))
    voice_var = tk.StringVar(value="Kadın")
    voice_combo = ttk.Combobox(frm, textvariable=voice_var, values=list(VOICE_MAP.keys()), state="readonly", width=10)
    voice_combo.grid(row=1, column=1, sticky="w", pady=(10, 0))

    # Başlat butonu
    ttk.Button(frm, text="Dönüştür (MP3 oluştur)", command=start_conversion).grid(
        row=2, column=0, columnspan=3, pady=15
    )

    root.mainloop()
