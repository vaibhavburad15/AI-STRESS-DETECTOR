import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Brain,
  ChevronRight,
  Loader2,
  Mic,
  MicOff,
  X,
  ShieldCheck,
} from 'lucide-react';
import api from '../services/api';
import type { Question, Test } from '../types';
import { BrowserAudioFeatureRecorder } from '../utils/audioFeatureRecorder';

interface Props {
  questions: Question[];
  onComplete: (result: Test) => void;
  onClose: () => void;
}

type Phase = 'permission' | 'intro' | 'ai-speaking' | 'user-answering' | 'submitting' | 'error';

const ANSWER_TIME = 30;

const CATEGORY_COLOR: Record<string, string> = {
  emotional:  '#f87171',
  physical:   '#fb923c',
  cognitive:  '#60a5fa',
  behavioral: '#34d399',
  stressors:  '#a78bfa',
};

export default function VideoAssessmentModal({ questions, onComplete, onClose }: Props) {
  const videoRef        = useRef<HTMLVideoElement>(null);
  const streamRef       = useRef<MediaStream | null>(null);
  const audioRecorderRef = useRef<BrowserAudioFeatureRecorder | null>(null);
  const recognitionRef  = useRef<any>(null);
  const answerStartMsRef = useRef<number>(0);
  const answerDurationsRef = useRef<number[]>([]);
  const answerWordCountsRef = useRef<number[]>([]);

  // Refs that shadow state — used inside stable callbacks to avoid stale closures
  const allResponsesRef = useRef<string[]>(Array(18).fill(''));
  const transcriptRef   = useRef('');
  const fallbackRef     = useRef('');
  const currentQRef     = useRef(0);
  const advancingRef    = useRef(false);  // prevents race between timer and button
  const isRecordingRef  = useRef(false);

  const [phase,          setPhase]          = useState<Phase>('permission');
  const [currentQ,       setCurrentQ]       = useState(0);
  const [transcript,     setTranscript]     = useState('');
  const [fallbackText,   setFallbackText]   = useState('');
  const [isAISpeaking,   setIsAISpeaking]   = useState(false);
  const [isRecording,    setIsRecording]    = useState(false);
  const [timeLeft,       setTimeLeft]       = useState(ANSWER_TIME);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [error,          setError]          = useState('');

  // Check SpeechRecognition support once on mount
  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) setSpeechSupported(false);
  }, []);

  // Attach camera stream to <video> whenever the element mounts/re-mounts
  useEffect(() => {
    if (videoRef.current && streamRef.current && !videoRef.current.srcObject) {
      videoRef.current.srcObject = streamRef.current;
    }
  });

  // ── Camera / mic permissions ────────────────────────────────────────────────
  const requestPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      try {
        const recorder = new BrowserAudioFeatureRecorder();
        await recorder.init(stream);
        audioRecorderRef.current = recorder;
      } catch (recorderError) {
        console.warn('Browser audio feature capture is unavailable:', recorderError);
        audioRecorderRef.current = null;
      }
      setPhase('intro');
    } catch {
      setError(
        'Camera and microphone access is required for the video assessment. ' +
        'Please grant permission in your browser and try again.'
      );
      setPhase('error');
    }
  };

  // ── Text-to-speech ──────────────────────────────────────────────────────────
  const speak = useCallback((text: string): Promise<void> => {
    return new Promise<void>(resolve => {
      if (!('speechSynthesis' in window)) { resolve(); return; }
      window.speechSynthesis.cancel();

      const u = new SpeechSynthesisUtterance(text);
      u.rate   = 0.87;
      u.pitch  = 1.0;
      u.volume = 1.0;

      const pickVoice = () => {
        const voices = window.speechSynthesis.getVoices();
        const v =
          voices.find(v => v.lang === 'en-US' && /female|samantha|emma|victoria|karen/i.test(v.name)) ||
          voices.find(v => v.lang === 'en-US') ||
          voices.find(v => v.lang.startsWith('en'));
        if (v) u.voice = v;
      };

      if (window.speechSynthesis.getVoices().length === 0) {
        window.speechSynthesis.addEventListener('voiceschanged', pickVoice, { once: true });
      } else {
        pickVoice();
      }

      u.onend  = () => { setIsAISpeaking(false); resolve(); };
      u.onerror = () => { setIsAISpeaking(false); resolve(); };
      setIsAISpeaking(true);
      window.speechSynthesis.speak(u);
    });
  }, []);

  // ── Speech recognition ──────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    transcriptRef.current = '';
    setTranscript('');
    answerStartMsRef.current = Date.now();
    isRecordingRef.current = true;
    audioRecorderRef.current?.startSegment();
    setIsRecording(true);
    setTimeLeft(ANSWER_TIME);

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setSpeechSupported(false); return; }

    const reco = new SR();
    reco.continuous     = true;
    reco.interimResults = true;
    reco.lang           = 'en-US';
    recognitionRef.current = reco;

    let finalText = '';
    reco.onresult = (e: any) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript + ' ';
        else interim += e.results[i][0].transcript;
      }
      const combined = (finalText + interim).trimStart();
      setTranscript(combined);
      transcriptRef.current = combined;
    };

    reco.onerror = (e: any) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        setSpeechSupported(false);
      }
    };

    try { reco.start(); } catch { /* ignore if already started */ }
  }, []);

  const stopListening = useCallback(() => {
    isRecordingRef.current = false;
    audioRecorderRef.current?.stopSegment();
    setIsRecording(false);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
  }, []);

  // ── Core assignment flow ────────────────────────────────────────────────────
  /**
   * Save the current answer and advance to the next question (or submit if last).
   * Uses refs throughout to avoid stale-closure issues inside the timer effect.
   */
  const saveAndAdvance = useCallback(async () => {
    if (advancingRef.current) return;  // prevent race between timer and Next button
    advancingRef.current = true;

    stopListening();
    window.speechSynthesis.cancel();

    const qIdx   = currentQRef.current;
    const answer = transcriptRef.current.trim() || fallbackRef.current.trim() || 'no response';
    const elapsedMs = Math.max(1000, Date.now() - (answerStartMsRef.current || Date.now()));
    answerDurationsRef.current[qIdx] = elapsedMs;
    answerWordCountsRef.current[qIdx] = answer.split(/\s+/).filter(Boolean).length;
    allResponsesRef.current[qIdx] = answer;

    if (qIdx < questions.length - 1) {
      // ── Ask next question ──
      const nextIdx = qIdx + 1;
      currentQRef.current = nextIdx;
      setCurrentQ(nextIdx);
      transcriptRef.current = '';
      fallbackRef.current   = '';
      setTranscript('');
      setFallbackText('');

      setPhase('ai-speaking');
      await speak(`Question ${nextIdx + 1}. ${questions[nextIdx].question}`);

      advancingRef.current = false; // allow the next question to be advanced
      startListening();
      setPhase('user-answering');
    } else {
      // ── All 18 questions done — submit ──
      setPhase('submitting');
      try {
        const totalWords = answerWordCountsRef.current.reduce((a, b) => a + (b || 0), 0);
        const totalMinutes = answerDurationsRef.current.reduce((a, b) => a + (b || 0), 0) / 60000;
        const speakingRateWpm = totalMinutes > 0 ? totalWords / totalMinutes : 140;

        const negativeLexicon = [
          'sad', 'depressed', 'hopeless', 'anxious', 'worried', 'angry', 'overwhelmed',
          'tired', 'panic', 'fear', 'stress', 'crying', 'hurt', 'pain', 'desperate'
        ];
        const joined = allResponsesRef.current.join(' ').toLowerCase();
        const negHits = negativeLexicon.reduce((count, term) => count + (joined.includes(term) ? 1 : 0), 0);
        const sentimentNegative = Math.min(1, negHits / 8);

        const audioStress = Math.min(1, Math.max(0, Math.abs(speakingRateWpm - 140) / 80));
        const browserAudioFeatures =
          (await audioRecorderRef.current?.finalize({
            speaking_rate_wpm: speakingRateWpm,
            stress: audioStress,
          })) ?? {
            speaking_rate_wpm: speakingRateWpm,
            stress: audioStress,
          };

        const { data } = await api.post('/api/user/video-test/submit', {
          verbal_responses: allResponsesRef.current,
          audio_features: browserAudioFeatures,
          facial_features: {
            stress: 0.5,
          },
          sentiment_features: {
            negative: sentimentNegative,
          },
        });
        onComplete(data as Test);
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
          err.message ||
          'Failed to analyze assessment. Please try again.'
        );
        setPhase('error');
      }
    }
  }, [questions, speak, startListening, stopListening, onComplete]);

  /** Starts the intro speech then jumps directly into Q1. */
  const startAssignment = useCallback(async () => {
    currentQRef.current  = 0;
    advancingRef.current = false;
    setCurrentQ(0);

    setPhase('ai-speaking');
    await speak(
      'Hello! This is your AI Stress Assignment. ' +
      'I will ask you 18 questions about your current stress levels. ' +
      'Please answer each question naturally and honestly. ' +
      'You may speak your answer or type it below. Let us begin.'
    );

    setTranscript('');
    setFallbackText('');
    transcriptRef.current = '';
    fallbackRef.current   = '';

    setPhase('ai-speaking');
    await speak(`Question 1. ${questions[0].question}`);
    startListening();
    setPhase('user-answering');
  }, [questions, speak, startListening]);

  // ── Countdown timer ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isRecording) return;
    if (timeLeft <= 0) { saveAndAdvance(); return; }
    const id = setInterval(() => setTimeLeft(s => s - 1), 1000);
    return () => clearInterval(id);
  }, [isRecording, timeLeft, saveAndAdvance]);

  // ── Cleanup on unmount ───────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      void audioRecorderRef.current?.dispose();
      audioRecorderRef.current = null;
      window.speechSynthesis.cancel();
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { /* ignore */ }
      }
    };
  }, []);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const progress = Math.round((currentQ / Math.max(questions.length, 1)) * 100);
  const currentQuestion = questions[currentQ];
  const catColor = currentQuestion ? CATEGORY_COLOR[currentQuestion.category] ?? '#60a5fa' : '#60a5fa';
  const catName  = currentQuestion
    ? currentQuestion.category.charAt(0).toUpperCase() + currentQuestion.category.slice(1)
    : '';

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-950 text-white">

      {/* ── Header ── */}
      <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900 px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">AI Stress Assignment</p>
            <p className="text-xs text-slate-400">Stress Assignment · Confidential</p>
          </div>
        </div>
        {phase !== 'submitting' && (
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* ── Progress bar ── */}
      {(phase === 'ai-speaking' || phase === 'user-answering') && (
        <div className="h-1 shrink-0 bg-slate-800">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex flex-1 flex-col overflow-auto">

        {/* ══ Permission screen ══ */}
        {phase === 'permission' && (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="w-full max-w-md text-center">
              <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-blue-600/20 ring-4 ring-blue-500/30">
                <Brain className="h-10 w-10 text-blue-400" />
              </div>
              <h2 className="mb-3 text-2xl font-bold">AI Stress Assignment</h2>
              <p className="mb-8 leading-relaxed text-slate-400">
                This assessment uses your camera and microphone to conduct an AI-powered stress assignment.
                The AI will speak each of the 18 questions aloud and analyse your verbal responses
                to predict your stress level using machine learning.
              </p>
              <div className="mb-8 grid grid-cols-3 gap-4">
                {[
                  { emoji: '🎤', label: 'Voice Analysis' },
                  { emoji: '📹', label: 'Live Camera' },
                  { emoji: '🔒', label: 'Private & Secure' },
                ].map(item => (
                  <div key={item.label} className="rounded-xl bg-slate-800 p-4">
                    <div className="mb-2 text-2xl">{item.emoji}</div>
                    <p className="text-xs font-medium text-slate-300">{item.label}</p>
                  </div>
                ))}
              </div>
              <button
                onClick={requestPermissions}
                className="w-full rounded-xl bg-blue-600 py-3.5 font-semibold text-white transition hover:bg-blue-500"
              >
                Allow Camera &amp; Microphone
              </button>
            </div>
          </div>
        )}

        {/* ══ Intro / ready screen ══ */}
        {phase === 'intro' && (
          <div className="flex flex-1 items-center justify-center p-6">
            <div className="w-full max-w-4xl">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Camera preview */}
                <div className="relative overflow-hidden rounded-2xl bg-slate-900 aspect-video">
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    playsInline
                    className="h-full w-full object-cover"
                    style={{ transform: 'scaleX(-1)' }}
                  />
                  <div className="absolute bottom-3 left-3 rounded-lg bg-black/60 px-2.5 py-1 text-xs text-white">
                    You
                  </div>
                </div>

                {/* AI intro panel */}
                <div className="flex flex-col items-center justify-center rounded-2xl bg-slate-900 p-8 text-center">
                  <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-blue-600/20 ring-4 ring-blue-500/30">
                    <Brain className="h-10 w-10 text-blue-400" />
                  </div>
                  <h3 className="mb-1 text-xl font-bold">Dr. AI</h3>
                  <p className="mb-1 text-sm text-slate-400">AI Stress Assignment</p>
                  <p className="mb-8 text-sm text-slate-500">18 Questions · ~15 mins · Confidential</p>
                  <button
                    onClick={startAssignment}
                    className="w-full rounded-xl bg-blue-600 py-3.5 font-semibold text-white transition hover:bg-blue-500"
                  >
                    Start Assignment
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══ Assignment screen (ai-speaking + user-answering) ══ */}
        {(phase === 'ai-speaking' || phase === 'user-answering') && (
          <div className="flex flex-1 flex-col gap-4 p-4 md:p-6">
            {/* Question counter row */}
            <div className="flex shrink-0 items-center justify-between">
              <span className="text-sm font-medium text-slate-400">
                Question{' '}
                <span className="font-bold text-white">{currentQ + 1}</span>
                {' '}of {questions.length}
              </span>
              <span className="text-sm font-semibold" style={{ color: catColor }}>
                {catName} Category
              </span>
            </div>

            {/* Two-column layout */}
            <div className="flex flex-1 flex-col gap-4 md:flex-row">
              {/* Left: camera feed */}
              <div className="relative overflow-hidden rounded-2xl bg-slate-900 md:w-[42%] aspect-video md:aspect-auto">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="h-full w-full object-cover"
                  style={{ transform: 'scaleX(-1)' }}
                />

                {/* Recording pill */}
                {isRecording && (
                  <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/70 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
                    Recording
                  </div>
                )}

                {/* Countdown */}
                {isRecording && (
                  <div className="absolute bottom-3 right-3 rounded-lg bg-black/70 px-3 py-1.5 backdrop-blur-sm">
                    <span
                      className={`text-sm font-bold tabular-nums ${
                        timeLeft <= 10 ? 'text-red-400' : 'text-white'
                      }`}
                    >
                      {timeLeft}s
                    </span>
                  </div>
                )}

                <div className="absolute bottom-3 left-3 rounded-lg bg-black/60 px-2.5 py-1 text-xs text-white">
                  You
                </div>
              </div>

              {/* Right: AI panel */}
              <div className="flex flex-1 flex-col rounded-2xl bg-slate-900 p-5">
                {/* AI avatar row */}
                <div className="mb-4 flex items-center gap-3 border-b border-slate-800 pb-4">
                  <div
                    className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-600/20 ${
                      isAISpeaking
                        ? 'ring-4 ring-blue-500/60 animate-pulse'
                        : 'ring-2 ring-blue-600/30'
                    }`}
                  >
                    <Brain className="h-6 w-6 text-blue-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-white">Dr. AI</p>
                    <p className="text-xs text-slate-400">
                      {isAISpeaking
                        ? '🔊 Speaking…'
                        : isRecording
                        ? '👂 Listening…'
                        : '⏳ Processing…'}
                    </p>
                  </div>

                  {/* Animated sound bars when AI speaks */}
                  {isAISpeaking && (
                    <div className="ml-auto flex items-end gap-0.5" style={{ height: 24 }}>
                      {[3, 6, 4, 8, 5, 7, 4, 6, 3].map((h, i) => (
                        <div
                          key={i}
                          className="w-1 rounded-full bg-blue-500"
                          style={{
                            height: `${h * 3}px`,
                            animation: `soundbar-${i % 3} 0.${4 + (i % 4)}s ease-in-out infinite alternate`,
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* Question text */}
                <div className="flex-1 flex flex-col justify-center">
                  <div className="rounded-xl bg-slate-800 p-5">
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-widest" style={{ color: catColor }}>
                      {currentQuestion?.category}
                    </p>
                    <p className="text-lg font-medium leading-relaxed text-white">
                      {currentQuestion?.question}
                    </p>
                    <p className="mt-3 text-xs text-slate-500">
                      Scale: 1 (Never / Not at all) → 5 (Always / Extremely)
                    </p>
                  </div>
                </div>

                {/* Answer area – shown when recording */}
                {phase === 'user-answering' && (
                  <div className="mt-4 space-y-3">
                    {/* Live transcript */}
                    <div className="min-h-[64px] rounded-xl bg-slate-800 p-4">
                      {transcript ? (
                        <p className="text-sm text-white">{transcript}</p>
                      ) : speechSupported ? (
                        <p className="text-sm italic text-slate-500">
                          <Mic className="mr-1 inline h-3.5 w-3.5" />
                          Speak your answer…
                        </p>
                      ) : (
                        <p className="text-sm italic text-slate-500">
                          Voice recognition unavailable — please type your answer below.
                        </p>
                      )}
                    </div>

                    {/* Fallback text input (always shown on unsupported browsers, optional otherwise) */}
                    {!speechSupported && (
                      <textarea
                        value={fallbackText}
                        onChange={e => {
                          setFallbackText(e.target.value);
                          fallbackRef.current = e.target.value;
                        }}
                        placeholder='Type your answer (e.g. "sometimes", "often", "never", "always")'
                        rows={2}
                        className="w-full resize-none rounded-xl border border-slate-700 bg-slate-800 p-4 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                      />
                    )}

                    {/* Bottom bar: mic status + Next button */}
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2">
                        {isRecording ? (
                          <>
                            <Mic className="h-4 w-4 animate-pulse text-red-400" />
                            <span className="text-xs text-slate-300">Recording</span>
                          </>
                        ) : (
                          <>
                            <MicOff className="h-4 w-4 text-slate-500" />
                            <span className="text-xs text-slate-500">Mic off</span>
                          </>
                        )}
                      </div>

                      <button
                        onClick={saveAndAdvance}
                        className="ml-auto flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500"
                      >
                        {currentQ < questions.length - 1 ? (
                          <>
                            <span>Next Question</span>
                            <ChevronRight className="h-4 w-4" />
                          </>
                        ) : (
                          <>
                            <span>Finish Assessment</span>
                            <ShieldCheck className="h-4 w-4" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══ Submitting / analysing screen ══ */}
        {phase === 'submitting' && (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="max-w-md text-center">
              <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-blue-600/20">
                <Loader2 className="h-10 w-10 animate-spin text-blue-400" />
              </div>
              <h2 className="mb-2 text-2xl font-bold">Analysing Your Assessment</h2>
              <p className="text-slate-400">
                Processing your verbal responses with AI and running the stress prediction model…
              </p>
              <div className="mt-6 flex justify-center gap-1.5">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="h-2 w-2 rounded-full bg-blue-500"
                    style={{ animation: `bounce 1s ${i * 0.2}s infinite` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ══ Error screen ══ */}
        {phase === 'error' && (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="max-w-md text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20">
                <X className="h-8 w-8 text-red-400" />
              </div>
              <h2 className="mb-2 text-xl font-semibold">Assessment Error</h2>
              <p className="mb-6 text-slate-400">{error}</p>
              <button
                onClick={onClose}
                className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-500"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Inline keyframes for sound bars + bounce dots */}
      <style>{`
        @keyframes soundbar-0 { from { transform: scaleY(0.4); } to { transform: scaleY(1.4); } }
        @keyframes soundbar-1 { from { transform: scaleY(0.6); } to { transform: scaleY(1.2); } }
        @keyframes soundbar-2 { from { transform: scaleY(0.5); } to { transform: scaleY(1.6); } }
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50%       { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
