import time
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np


def resample_audio(data, old_speed, new_speed, position):
    if new_speed <= 0:
        raise ValueError("new_speed must be positive")
    if old_speed == new_speed:
        return (data, position)

    n = data.shape[0]
    new_n = int(n / new_speed)

    x_old = np.linspace(0, 1, n)
    x_new = np.linspace(0, 1, new_n)

    if data.ndim == 1:
        new_data = np.interp(x_new, x_old, data)
    else:
        channels = [
            np.interp(x_new, x_old, data[:, ch])
            for ch in range(data.shape[1])
        ]
        new_data = np.stack(channels, axis=1)

    new_index = int(position / new_speed)
    new_index = max(0, min(new_index, new_data.shape[0] - 1))

    return (new_data, new_index)


class AudioController:
    def __init__(self):
        self.data = None        # numpy array (frames, channels)
        self.original_data = None
        self.samplerate = None

        self.position = 0       # sample index for original speed
        self.play_index = 0     # sample index for current speed
        self.playing = False
        self.speed = 1.0

        self.stream = None
        self.lock = threading.RLock()

    def load(self, filepath):
        data, sr = sf.read(filepath, always_2d=True)
        self.stop()

        with self.lock:
            self.data = data
            self.original_data = data
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

    # ----- Change playback speed -----
    def set_speed(self, speed):
        if self.data is not None:
            with self.lock:
                self.data, self.play_index = resample_audio(
                    self.original_data,
                    self.speed,
                    speed,
                    self.position,
                )

        self.speed = speed
        print(f"[Audio] speed set to {speed:.2f}x")

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

