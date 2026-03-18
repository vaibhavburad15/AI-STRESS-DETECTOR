const FRAME_MS = 25;
const HOP_MS = 10;
const TARGET_SAMPLE_RATE = 16000;
const MIN_F0_HZ = 70;
const MAX_F0_HZ = 350;
const N_MELS = 26;
const N_MFCC = 13;

type SpectralFrame = {
  centroid: number;
  bandwidth: number;
  rolloff: number;
  flatness: number;
  mfcc: number[];
};

type RecorderAudioContext = AudioContext & {
  createScriptProcessor?: (
    bufferSize: number,
    numberOfInputChannels: number,
    numberOfOutputChannels: number,
  ) => ScriptProcessorNode;
};

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

const MFCC_MEAN_KEYS = Array.from(
  { length: N_MFCC },
  (_, index) => `mfcc_${String(index + 1).padStart(2, '0')}_mean`,
);
const MFCC_STD_KEYS = Array.from(
  { length: N_MFCC },
  (_, index) => `mfcc_${String(index + 1).padStart(2, '0')}_std`,
);
const MFCC_DELTA_MEAN_KEYS = Array.from(
  { length: N_MFCC },
  (_, index) => `mfcc_delta_${String(index + 1).padStart(2, '0')}_mean`,
);
const MFCC_DELTA_STD_KEYS = Array.from(
  { length: N_MFCC },
  (_, index) => `mfcc_delta_${String(index + 1).padStart(2, '0')}_std`,
);
const MFCC_FEATURE_KEYS = [
  ...MFCC_MEAN_KEYS,
  ...MFCC_STD_KEYS,
  ...MFCC_DELTA_MEAN_KEYS,
  ...MFCC_DELTA_STD_KEYS,
];

const melFilterbankCache = new Map<string, number[][]>();
const dctBasisCache = new Map<number, number[][]>();

const safeMean = (values: number[]): number =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

const safeStd = (values: number[]): number => {
  if (!values.length) return 0;
  const mean = safeMean(values);
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
};

const safePercentile = (values: number[], percentile: number): number => {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.round((percentile / 100) * (sorted.length - 1))),
  );
  return sorted[index];
};

const safeRange = (values: number[]): number => {
  if (!values.length) return 0;
  let minValue = values[0];
  let maxValue = values[0];
  for (let index = 1; index < values.length; index += 1) {
    minValue = Math.min(minValue, values[index]);
    maxValue = Math.max(maxValue, values[index]);
  }
  return maxValue - minValue;
};

const zeroMfccFeatures = (): Record<string, number> => {
  const features: Record<string, number> = {};
  for (const key of MFCC_FEATURE_KEYS) {
    features[key] = 0;
  }
  return features;
};

const mergeChunks = (chunks: Float32Array[]): Float32Array => {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
};

const downsampleSignal = (
  samples: Float32Array,
  originalSampleRate: number,
  targetSampleRate: number,
): Float32Array => {
  if (originalSampleRate <= targetSampleRate) {
    return samples.slice();
  }

  const ratio = originalSampleRate / targetSampleRate;
  const newLength = Math.max(1, Math.round(samples.length / ratio));
  const result = new Float32Array(newLength);

  let offsetBuffer = 0;
  for (let index = 0; index < newLength; index += 1) {
    const nextOffsetBuffer = Math.min(samples.length, Math.round((index + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let sampleIndex = offsetBuffer; sampleIndex < nextOffsetBuffer; sampleIndex += 1) {
      sum += samples[sampleIndex];
      count += 1;
    }
    result[index] = count > 0 ? sum / count : 0;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
};

const normalizeSignal = (samples: Float32Array): Float32Array => {
  if (samples.length === 0) return samples;

  let mean = 0;
  for (let index = 0; index < samples.length; index += 1) {
    mean += samples[index];
  }
  mean /= samples.length;

  const centered = new Float32Array(samples.length);
  let peak = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index] - mean;
    centered[index] = value;
    peak = Math.max(peak, Math.abs(value));
  }

  if (peak <= 0) return centered;

  for (let index = 0; index < centered.length; index += 1) {
    centered[index] /= peak;
  }
  return centered;
};

const frameSignal = (
  samples: Float32Array,
  frameLength: number,
  hopLength: number,
): Float32Array[] => {
  const padded =
    samples.length < frameLength
      ? (() => {
          const next = new Float32Array(frameLength);
          next.set(samples);
          return next;
        })()
      : samples;

  const frames: Float32Array[] = [];
  for (let start = 0; start <= padded.length - frameLength; start += hopLength) {
    frames.push(padded.slice(start, start + frameLength));
  }
  return frames;
};

const computeRms = (frame: Float32Array): number => {
  let sumSquares = 0;
  for (let index = 0; index < frame.length; index += 1) {
    sumSquares += frame[index] * frame[index];
  }
  return Math.sqrt(sumSquares / frame.length);
};

const computeZeroCrossingRate = (frame: Float32Array): number => {
  if (frame.length < 2) return 0;
  let crossings = 0;
  for (let index = 1; index < frame.length; index += 1) {
    if ((frame[index - 1] >= 0 && frame[index] < 0) || (frame[index - 1] < 0 && frame[index] >= 0)) {
      crossings += 1;
    }
  }
  return crossings / (frame.length - 1);
};

const hzToMel = (valueHz: number): number => 2595 * Math.log10(1 + valueHz / 700);

const melToHz = (valueMel: number): number => 700 * (10 ** (valueMel / 2595) - 1);

const buildMelFilterbank = (sampleRate: number, binCount: number): number[][] => {
  const cacheKey = `${sampleRate}:${binCount}:${N_MELS}`;
  const cached = melFilterbankCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const maxMel = hzToMel(sampleRate / 2);
  const melPoints = Array.from(
    { length: N_MELS + 2 },
    (_, index) => (index / (N_MELS + 1)) * maxMel,
  );
  const hzPoints = melPoints.map(melToHz);
  const freqStep = (sampleRate / 2) / Math.max(1, binCount - 1);
  const binIndices = hzPoints.map((hz) => Math.min(binCount - 1, Math.max(0, Math.floor(hz / freqStep))));

  const filterbank = Array.from({ length: N_MELS }, () => Array(binCount).fill(0));
  for (let melIndex = 0; melIndex < N_MELS; melIndex += 1) {
    const start = binIndices[melIndex];
    const center = Math.max(start + 1, binIndices[melIndex + 1]);
    const end = Math.max(center + 1, binIndices[melIndex + 2]);

    for (let freqIndex = start; freqIndex < Math.min(center, binCount); freqIndex += 1) {
      filterbank[melIndex][freqIndex] = (freqIndex - start) / Math.max(center - start, 1);
    }
    for (let freqIndex = center; freqIndex < Math.min(end, binCount); freqIndex += 1) {
      filterbank[melIndex][freqIndex] = (end - freqIndex) / Math.max(end - center, 1);
    }

    const weightSum = filterbank[melIndex].reduce((sum, value) => sum + value, 0);
    if (weightSum > 0) {
      for (let freqIndex = 0; freqIndex < binCount; freqIndex += 1) {
        filterbank[melIndex][freqIndex] /= weightSum;
      }
    }
  }

  melFilterbankCache.set(cacheKey, filterbank);
  return filterbank;
};

const buildDctBasis = (inputSize: number): number[][] => {
  const cached = dctBasisCache.get(inputSize);
  if (cached) {
    return cached;
  }

  const scale = Math.sqrt(2 / inputSize);
  const basis = Array.from({ length: N_MFCC }, (_, rowIndex) =>
    Array.from({ length: inputSize }, (_, columnIndex) =>
      scale * Math.cos((Math.PI / inputSize) * (columnIndex + 0.5) * rowIndex),
    ),
  );
  for (let columnIndex = 0; columnIndex < inputSize; columnIndex += 1) {
    basis[0][columnIndex] *= 1 / Math.sqrt(2);
  }

  dctBasisCache.set(inputSize, basis);
  return basis;
};

const computeMfccFromPowerBins = (powerBins: number[], sampleRate: number): number[] => {
  if (!powerBins.length) {
    return Array(N_MFCC).fill(0);
  }

  const filterbank = buildMelFilterbank(sampleRate, powerBins.length);
  const dctBasis = buildDctBasis(filterbank.length);
  const logMelEnergy = filterbank.map((filter) => {
    let sum = 0;
    for (let index = 0; index < powerBins.length; index += 1) {
      sum += powerBins[index] * filter[index];
    }
    return Math.log(Math.max(sum, 1e-10));
  });

  return dctBasis.map((row) => {
    let coefficient = 0;
    for (let index = 0; index < row.length; index += 1) {
      coefficient += row[index] * logMelEnergy[index];
    }
    return coefficient;
  });
};

const estimatePitchTrack = (
  frames: Float32Array[],
  sampleRate: number,
  rmsValues: number[],
  energyThreshold: number,
): number[] => {
  if (!frames.length) return [];

  const frameLength = frames[0].length;
  const minLag = Math.max(1, Math.floor(sampleRate / MAX_F0_HZ));
  const maxLag = Math.min(frameLength - 1, Math.floor(sampleRate / MIN_F0_HZ));
  const window = new Float32Array(frameLength);
  for (let index = 0; index < frameLength; index += 1) {
    window[index] = 0.5 - 0.5 * Math.cos((2 * Math.PI * index) / Math.max(1, frameLength - 1));
  }

  return frames.map((frame, frameIndex) => {
    if (rmsValues[frameIndex] < energyThreshold) {
      return Number.NaN;
    }

    let mean = 0;
    for (let index = 0; index < frameLength; index += 1) {
      mean += frame[index];
    }
    mean /= frameLength;

    const windowed = new Float32Array(frameLength);
    let peakAmplitude = 0;
    for (let index = 0; index < frameLength; index += 1) {
      const value = (frame[index] - mean) * window[index];
      windowed[index] = value;
      peakAmplitude = Math.max(peakAmplitude, Math.abs(value));
    }
    if (peakAmplitude < 1e-5) {
      return Number.NaN;
    }

    let reference = 0;
    for (let index = 0; index < frameLength; index += 1) {
      reference += windowed[index] * windowed[index];
    }
    if (reference <= 0) {
      return Number.NaN;
    }

    let bestLag = -1;
    let bestAutocorr = -Infinity;
    for (let lag = minLag; lag <= maxLag; lag += 1) {
      let autocorr = 0;
      for (let index = 0; index < frameLength - lag; index += 1) {
        autocorr += windowed[index] * windowed[index + lag];
      }
      if (autocorr > bestAutocorr) {
        bestAutocorr = autocorr;
        bestLag = lag;
      }
    }

    if (bestLag <= 0 || bestAutocorr / (reference + 1e-8) < 0.3) {
      return Number.NaN;
    }

    return sampleRate / bestLag;
  });
};

const computeSpectralFrame = (
  dbBins: Float32Array,
  sampleRate: number,
): SpectralFrame => {
  if (!dbBins.length) {
    return {
      centroid: 0,
      bandwidth: 0,
      rolloff: 0,
      flatness: 0,
      mfcc: Array(N_MFCC).fill(0),
    };
  }

  const amplitudes = new Float32Array(dbBins.length);
  const powerBins = new Array<number>(dbBins.length);
  let spectralSum = 0;
  let weightedSum = 0;
  let logSum = 0;
  const freqStep = (sampleRate / 2) / Math.max(1, dbBins.length - 1);

  for (let index = 0; index < dbBins.length; index += 1) {
    const db = Number.isFinite(dbBins[index]) ? dbBins[index] : -160;
    const amplitude = Math.pow(10, db / 20);
    amplitudes[index] = amplitude;
    powerBins[index] = amplitude * amplitude;
    spectralSum += amplitude;
    weightedSum += amplitude * (index * freqStep);
    logSum += Math.log(Math.max(amplitude, 1e-8));
  }

  if (spectralSum <= 0) {
    return {
      centroid: 0,
      bandwidth: 0,
      rolloff: 0,
      flatness: 0,
      mfcc: Array(N_MFCC).fill(0),
    };
  }

  const centroid = weightedSum / spectralSum;
  let bandwidthNumerator = 0;
  let cumulative = 0;
  let rolloff = 0;
  const rolloffTarget = 0.85 * spectralSum;

  for (let index = 0; index < amplitudes.length; index += 1) {
    const frequency = index * freqStep;
    bandwidthNumerator += amplitudes[index] * (frequency - centroid) ** 2;
    cumulative += amplitudes[index];
    if (rolloff === 0 && cumulative >= rolloffTarget) {
      rolloff = frequency;
    }
  }

  return {
    centroid,
    bandwidth: Math.sqrt(bandwidthNumerator / spectralSum),
    rolloff,
    flatness: Math.exp(logSum / amplitudes.length) / (spectralSum / amplitudes.length),
    mfcc: computeMfccFromPowerBins(powerBins, sampleRate),
  };
};

const computeMfccFeatures = (spectralFrames: SpectralFrame[]): Record<string, number> => {
  if (!spectralFrames.length) {
    return zeroMfccFeatures();
  }

  const mfccFrames = spectralFrames.map((frame) => frame.mfcc);
  const frameCount = mfccFrames.length;
  const lastIndex = frameCount - 1;
  const features: Record<string, number> = {};

  for (let coeffIndex = 0; coeffIndex < N_MFCC; coeffIndex += 1) {
    const values = mfccFrames.map((frame) => frame[coeffIndex] ?? 0);
    const deltas = values.map((value, index) => {
      if (frameCount === 1) {
        return 0;
      }
      if (index === 0) {
        return values[1] - value;
      }
      if (index === lastIndex) {
        return value - values[lastIndex - 1];
      }
      return (values[index + 1] - values[index - 1]) / 2;
    });

    features[MFCC_MEAN_KEYS[coeffIndex]] = safeMean(values);
    features[MFCC_STD_KEYS[coeffIndex]] = safeStd(values);
    features[MFCC_DELTA_MEAN_KEYS[coeffIndex]] = safeMean(deltas);
    features[MFCC_DELTA_STD_KEYS[coeffIndex]] = safeStd(deltas);
  }

  return features;
};

const extractFeatureVector = (
  mergedSamples: Float32Array,
  originalSampleRate: number,
  spectralFrames: SpectralFrame[],
): Record<string, number> | null => {
  if (!mergedSamples.length) return null;

  const durationSec = mergedSamples.length / originalSampleRate;
  if (durationSec <= 0) return null;

  const analysisSampleRate = Math.min(originalSampleRate, TARGET_SAMPLE_RATE);
  const analysisSamples = normalizeSignal(
    downsampleSignal(mergedSamples, originalSampleRate, analysisSampleRate),
  );

  const frameLength = Math.max(1, Math.round((analysisSampleRate * FRAME_MS) / 1000));
  const hopLength = Math.max(1, Math.round((analysisSampleRate * HOP_MS) / 1000));
  const frames = frameSignal(analysisSamples, frameLength, hopLength);
  if (!frames.length) return null;

  const rmsValues = frames.map(computeRms);
  const zcrValues = frames.map(computeZeroCrossingRate);
  const positiveRms = rmsValues.filter((value) => value > 0);
  const medianRms = positiveRms.length ? safePercentile(positiveRms, 50) : 0;
  const energyThreshold = Math.max(0.02, 0.35 * medianRms);
  const voicedMask = rmsValues.map((value) => value >= energyThreshold);
  const voicedRms = rmsValues.filter((_, index) => voicedMask[index]);

  const pitchTrack = estimatePitchTrack(frames, analysisSampleRate, rmsValues, energyThreshold);
  const validPitch = pitchTrack.filter((value) => Number.isFinite(value));
  const pitchDelta = validPitch.slice(1).map((value, index) => Math.abs(value - validPitch[index]));
  const rmsDelta = voicedRms.slice(1).map((value, index) => Math.abs(value - voicedRms[index]));

  const speechTurnStarts = voicedMask.reduce((count, isVoiced, index) => {
    if (!isVoiced) return count;
    return count + (index === 0 || !voicedMask[index - 1] ? 1 : 0);
  }, 0);

  const firstHalf = rmsValues.slice(0, Math.max(1, Math.floor(rmsValues.length / 2)));
  const secondHalf = rmsValues.slice(Math.floor(rmsValues.length / 2));

  const centroidValues = spectralFrames.map((frame) => frame.centroid);
  const bandwidthValues = spectralFrames.map((frame) => frame.bandwidth);
  const rolloffValues = spectralFrames.map((frame) => frame.rolloff);
  const flatnessValues = spectralFrames.map((frame) => frame.flatness);
  const mfccFeatures = computeMfccFeatures(spectralFrames);

  return {
    duration_sec: durationSec,
    rms_mean: safeMean(rmsValues),
    rms_std: safeStd(rmsValues),
    rms_p90: safePercentile(rmsValues, 90),
    zcr_mean: safeMean(zcrValues),
    zcr_std: safeStd(zcrValues),
    centroid_mean: safeMean(centroidValues),
    centroid_std: safeStd(centroidValues),
    bandwidth_mean: safeMean(bandwidthValues),
    bandwidth_std: safeStd(bandwidthValues),
    rolloff_mean: safeMean(rolloffValues),
    rolloff_std: safeStd(rolloffValues),
    flatness_mean: safeMean(flatnessValues),
    flatness_std: safeStd(flatnessValues),
    ...mfccFeatures,
    pitch_mean: safeMean(validPitch),
    pitch_std: safeStd(validPitch),
    pitch_range: safeRange(validPitch),
    pitched_frame_ratio: validPitch.length / frames.length,
    jitter_local:
      validPitch.length > 1
        ? safeMean(
            pitchDelta.map((delta, index) => delta / Math.max(validPitch[index], 1e-6)),
          )
        : 0,
    shimmer_local:
      voicedRms.length > 1
        ? safeMean(
            rmsDelta.map((delta, index) => delta / Math.max(voicedRms[index], 1e-6)),
          )
        : 0,
    pause_ratio: 1 - voicedMask.filter(Boolean).length / voicedMask.length,
    voiced_ratio: voicedMask.filter(Boolean).length / voicedMask.length,
    voiced_rms_mean: safeMean(voicedRms),
    voiced_rms_std: safeStd(voicedRms),
    speech_turns_per_sec: speechTurnStarts / durationSec,
    energy_drift: safeMean(secondHalf) - safeMean(firstHalf),
  };
};

export class BrowserAudioFeatureRecorder {
  private audioContext: RecorderAudioContext | null = null;

  private sourceNode: MediaStreamAudioSourceNode | null = null;

  private analyserNode: AnalyserNode | null = null;

  private processorNode: ScriptProcessorNode | null = null;

  private sampleChunks: Float32Array[] = [];

  private spectralFrames: SpectralFrame[] = [];

  private capturing = false;

  async init(stream: MediaStream): Promise<void> {
    if (this.audioContext) return;

    const AudioContextCtor = window.AudioContext ?? window.webkitAudioContext;
    if (!AudioContextCtor) {
      throw new Error('AudioContext is not supported in this browser.');
    }

    const audioContext = new AudioContextCtor({ sampleRate: TARGET_SAMPLE_RATE }) as RecorderAudioContext;
    await audioContext.resume();

    const createProcessor = audioContext.createScriptProcessor?.bind(audioContext);
    if (!createProcessor) {
      await audioContext.close();
      throw new Error('ScriptProcessorNode is not supported in this browser.');
    }

    const sourceNode = audioContext.createMediaStreamSource(stream);
    const analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 2048;
    analyserNode.smoothingTimeConstant = 0;

    const processorNode = createProcessor(2048, 1, 1);
    const spectralBuffer = new Float32Array(analyserNode.frequencyBinCount);

    processorNode.onaudioprocess = (event: AudioProcessingEvent) => {
      const output = event.outputBuffer.getChannelData(0);
      output.fill(0);

      if (!this.capturing) {
        return;
      }

      const input = event.inputBuffer.getChannelData(0);
      this.sampleChunks.push(new Float32Array(input));

      analyserNode.getFloatFrequencyData(spectralBuffer);
      this.spectralFrames.push(computeSpectralFrame(spectralBuffer, audioContext.sampleRate));
    };

    sourceNode.connect(analyserNode);
    analyserNode.connect(processorNode);
    processorNode.connect(audioContext.destination);

    this.audioContext = audioContext;
    this.sourceNode = sourceNode;
    this.analyserNode = analyserNode;
    this.processorNode = processorNode;
  }

  startSegment(): void {
    this.capturing = true;
  }

  stopSegment(): void {
    this.capturing = false;
  }

  async finalize(extraFeatures: Record<string, number> = {}): Promise<Record<string, number> | null> {
    this.capturing = false;
    if (!this.audioContext) {
      return null;
    }

    const mergedSamples = mergeChunks(this.sampleChunks);
    const features = extractFeatureVector(
      mergedSamples,
      this.audioContext.sampleRate,
      this.spectralFrames,
    );
    if (!features) {
      return null;
    }

    return {
      ...features,
      ...extraFeatures,
    };
  }

  async dispose(): Promise<void> {
    this.capturing = false;

    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode.onaudioprocess = null;
      this.processorNode = null;
    }
    if (this.analyserNode) {
      this.analyserNode.disconnect();
      this.analyserNode = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    this.sampleChunks = [];
    this.spectralFrames = [];
  }
}
