import time
import threading
import sounddevice as sd
import soundfile as sf


class AudioController:
    def __init__(self):
        self.data = None        # numpy array (frames, channels)
        self.samplerate = None

        self.position = 0       # sample index
        self.playing = False

        self.stream = None
        self.lock = threading.RLock()

    def load(self, filepath):
        data, sr = sf.read(filepath, always_2d=True)
        self.stop()

        with self.lock:
            self.data = data
            self.samplerate = sr
            self.position = 0

        print(f"[Audio] loaded ({len(data)/sr:.2f}s)")

    # ----- Stream -----
    def _callback(self, outdata, frames, time_info, status):
        with self.lock:
            if not self.playing or self.data is None:
                outdata[:] = 0
                return

            end = self.position + frames
            chunk = self.data[self.position:end]

            if len(chunk) < frames:
                outdata[:len(chunk)] = chunk
                outdata[len(chunk):] = 0
                self.playing = False
            else:
                 outdata[:] = chunk
            
            self.position = end

    def _ensure_stream(self):
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.data.shape[1],
                callback=self._callback,
            )
            self.stream.start()

    # ----- Play/Pause -----
    def play_pause(self):
        if self.data is None:
            return

        with self.lock:
            self._ensure_stream()
            self.playing = not self.playing

        print(f"[Audio] {'playing' if self.playing else 'paused'} ({self.get_curr_time():.2f}s)")

    def stop(self):
        with self.lock:
            self.playing = False
            self.position = 0

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    # ----- Seek/Query -----
    def seek(self, delta):
        if self.data is None:
            return

        with self.lock:
            delta_samples = int(delta * self.samplerate)
            self.position += delta_samples
            self.position = max(0, min(self.position, len(self.data)))
        
        print(f"[Audio] seek ({self.get_curr_time():.2f}s)")

    def get_curr_time(self):
        if self.samplerate is None:
            return 0.0
        return self.position / self.samplerate

    def get_duration(self):
        if self.data is None:
            return 0.0
        return len(self.data) / self.samplerate

