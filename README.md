# İngilizce Videodan Türkçe Dublaj: Whisper + ChatGPT + Edge-TTS

Bu proje, yerel bilgisayarında şu sırayı gerçekleştirmek için basit bir pipeline sağlar:

1. **Whisper** ile İngilizce video sesini zaman uyumlu **SRT altyazıya** çevirme  
2. **ChatGPT** ile (manuel) SRT metnindeki hataları düzeltme / Türkçe çeviri üretme  
3. Düzeltilmiş **Türkçe .srt** dosyasını Python ve **Edge-TTS** kullanarak **Türkçe ses dosyasına (dublaj)** çevirme  
4. İsteğe bağlı: **FFmpeg** ile bu Türkçe sesi videoya **ek ses parçası** olarak gömme

> Not: Bu repo, her adımı otomatikleştirmek yerine, **pratik bir workflow** ve yardımcı scriptler sunar.  
> Whisper ve ChatGPT ile metin düzeltme / çeviri kısmı **manuel** yapılır.

---

## 🧰 Gereksinimler

- Python 3.13.x (veya edge-tts ile uyumlu bir 3.x sürümü)
- `pip`
- (Whisper için) PyTorch + `whisper`
- (İsteğe bağlı) [FFmpeg](https://ffmpeg.org/) – videoya ses eklemek için

Python paketleri:

```bash
pip install edge-tts srt
# Whisper için (zaten yüklüyse tekrar gerek yok)
pip install -U openai-whisper
````

Ayrıca bu repodaki `requirements.txt`:

```text
edge-tts
srt
openai-whisper
```

---

## 🔁 Genel Akış

### 1. İngilizce ses → İngilizce SRT (Whisper)

Örneğin `input_en.mp3` dosyan olsun:

```bash
python -m whisper input_en.mp3 --model large --language en --task transcribe --output_format srt
```

Bu komut, aynı klasöre yaklaşık şu isimde bir dosya üretir:

```text
input_en.srt
```

### Alternatif altyazı oluşturma
```bash
python -m whisper "english.mp3" --model large --language en --task transcribe
```
⚠️ Bu komut %100 çalışır, çünkü whisper komutunu PATH'e eklemeye gerek kalmaz.

Bu işlem bitince klasörde otomatik olarak şunlar oluşacak:

uscap.srt → ✔️ İngilizce altyazı

uscap.txt → metin dosyası

uscap.vtt → web altyazısı

---

### 2. İngilizce SRT’yi düzeltme (ChatGPT ile manuel)

Bu adım **bilerek manuel** bırakılmıştır:

1. `input_en.srt` içindeki metni al
2. ChatGPT’ye yapıştır:

   * “Lütfen aşağıdaki altyazı metnini imla/hata açısından düzelt.”
3. Düzeltmiş İngilizce metni istersen tekrar `.srt` formatında düzenle

İstersen bu aşamada:

* İngilizce → Türkçe çeviriyi de ChatGPT’den isteyebilirsin
* Çeviriyi **SRT formatına sadık** olacak şekilde al: zaman kodları aynı, içerik Türkçe

Sonuçta elinde şu dosya olmalı:

```text
subtitles_tr.srt   # Türkçe, zaman kodları korunmuş altyazı
```

---

### 3. Türkçe SRT → Türkçe ses (Edge-TTS)

`subtitles_tr.srt` dosyasını `scripts/srt_to_turkish_tts.py` ile aynı klasöre koy veya yolu ona göre güncelle.

Script: [`scripts/srt_to_turkish_tts.py`](scripts/srt_to_turkish_tts.py)

```bash
cd scripts
python srt_to_turkish_tts.py
```

Varsayılan ayarlar:

* Girdi: `altyazi.srt` (aynı klasörde)
* Çıktı: `turkce_ses.wav`
* Ses: `tr-TR-EmelNeural` (Türkçe kadın sesi)

Bu dosyayı **dublaj** olarak kullanacağız.

---

### 4. Türkçe sesi videoya eklemek (FFmpeg)

Elinde:

* Orijinal video: `video.mp4`
* Üretilen Türkçe ses: `turkce_ses.wav`

Videoya **ek ses parçası** olarak eklemek için:

```bash
ffmpeg -i video.mp4 -i turkce_ses.wav \
  -map 0:v -map 0:a -map 1:a \
  -c:v copy -c:a aac -shortest \
  video_tr_dub.mp4
```

Bu komut:

* Görüntüyü yeniden kodlamadan **kopyalar** (`-c:v copy`)
* Orijinal ses + Türkçe ses olacak şekilde birden fazla ses parçası ekler
* Kısaysa ses veya video farkında, en kısa olana göre kırpar (`-shortest`)

Sadece Türkçe sesli bir çıktı istersen:

```bash
ffmpeg -i video.mp4 -i turkce_ses.wav \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -shortest \
  video_tr_only.mp4
```

---

## 📜 `scripts/srt_to_turkish_tts.py`

Bu script, Python 3.13 ile uyumlu olacak şekilde **pydub kullanmadan**, sadece `edge-tts`, `srt` ve standart `wave` modülüyle çalışır.

```python
import asyncio
import wave
import os
import srt
import edge_tts

# ==========================
# Kullanıcı ayarları
# ==========================

SRT_DOSYASI = "altyazi.srt"        # Türkçe altyazı dosyan
CIKTI_DOSYASI = "turkce_ses.wav"   # Üretilecek ses dosyası
VOICE = "tr-TR-EmelNeural"         # Türkçe kadın ses


async def generate_segment(text: str, filename: str):
    """
    Edge TTS kullanarak verilen metni WAV dosyasına kaydeder.
    """
    communicate = edge_tts.Communicate(text=text, voice=VOICE)
    await communicate.save(filename)


def merge_waves(segments, output_path):
    """
    Segment WAV dosyalarını zaman damgalarına göre birleştirir.
    Edge TTS'in ürettiği WAV'ler tipik olarak 24000 Hz, mono, 16-bit olur.
    """
    framerate = 24000
    sampwidth = 2
    nchannels = 1

    final_frames = bytearray()

    for start_ms, wav_path in segments:
        # Şu ana kadar üretilen sesin süresi (ms)
        current_ms = int(len(final_frames) / (framerate * sampwidth * nchannels) * 1000)

        # Gerekirse sessizlik ekle
        if start_ms > current_ms:
            silence_ms = start_ms - current_ms
            silence_samples = int(framerate * (silence_ms / 1000))
            final_frames.extend(b"\x00\x00" * silence_samples)

        # WAV dosyasını ekle
        with wave.open(wav_path, "rb") as w:
            final_frames.extend(w.readframes(w.getnframes()))

    # Son WAV dosyasını yaz
    with wave.open(output_path, "wb") as out:
        out.setnchannels(nchannels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        out.writeframes(final_frames)

    print("Tamamlandı:", output_path)


async def main():
    # 1) SRT dosyasını oku
    with open(SRT_DOSYASI, "r", encoding="utf-8") as f:
        subtitles = list(srt.parse(f.read()))

    segments = []

    # 2) Her altyazı satırı için Edge TTS ile geçici ses üret
    for i, sub in enumerate(subtitles):
        text = sub.content.replace("\n", " ").strip()
        if not text:
            continue

        start_ms = int(sub.start.total_seconds() * 1000)
        temp_file = f"segment_{i}.wav"

        print(f"[{i+1}/{len(subtitles)}] Ses üretiliyor: {text!r}")

        await generate_segment(text, temp_file)
        segments.append((start_ms, temp_file))

    # 3) Segmentleri zaman damgalarına göre birleştir
    merge_waves(segments, CIKTI_DOSYASI)

    # 4) Geçici dosyaları temizle
    for _, fpath in segments:
        if os.path.exists(fpath):
            os.remove(fpath)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔍 Notlar

* **Whisper hatalarının düzeltilmesi** ve **Türkçe çeviri** adımı bilinçli olarak manuel:

  * ChatGPT veya başka bir LLM ile dilediğin prompt’u kullanabilirsin.
  * İstersen sadece yazım hatası düzelt, istersen aynı anda çeviri ve sadeleştirme iste.
* Edge-TTS internet bağlantısı gerektirir; tamamen offline bir çözüm istersen, Silero TTS gibi local modeller eklenebilir (bu repo şimdilik Edge-TTS odaklı).

---

## 🧾 Lisans

İstediğin lisansı buraya ekleyebilirsin (MIT, Apache-2.0, vb.).

```
