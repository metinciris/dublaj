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
