#!/bin/bash
# Usage: ./build.sh <spec_id>   (spec in specs/<spec_id>.json) -> out/<id>_final.mp4 + out/<id>_cover.jpg
set -e
cd "$(dirname "$0")"; ID=$1
python3 -c "import kokoro_onnx, soundfile, scipy" 2>/dev/null || pip install -q --break-system-packages kokoro-onnx soundfile scipy
[ -s kokoro.onnx ] || curl -sSL -o kokoro.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s voices.bin ] || curl -sSL -o voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
if [ ! -d fonts/anton ]; then mkdir -p fonts && (cd fonts && for p in anton playfair-display; do npm pack -q @fontsource/$p >/dev/null && tar xzf fontsource-$p-*.tgz && mv package $p; done); fi
mkdir -p out
if [ -f out/${ID}.json ] && [ out/${ID}.json -nt specs/${ID}.json ] && [ -f out/${ID}_00.wav ]; then echo "reusing voice"; else python3 vo.py $ID; fi
python3 engine.py $ID
python3 music.py $ID
python3 cover.py $ID
ffmpeg -y -loglevel error -i out/${ID}_silent.mp4 -i out/${ID}_mix.wav -c:v libx264 -preset medium -crf 22 -maxrate 6500k -bufsize 13M -pix_fmt yuv420p -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart out/${ID}_final.mp4
ls -la out/${ID}_final.mp4 out/${ID}_cover.jpg
