import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Camera,
  ChevronRight,
  Loader2,
  Mic,
  MicOff,
  ShieldCheck,
  Sparkles,
  Video,
  X,
} from 'lucide-react';

import api from '../services/api';
import type { Question, Test } from '../types';
import { BrowserAudioFeatureRecorder } from '../utils/audioFeatureRecorder';
import stressLogo from '../../assets/stress logo.png';

interface Props {
  questions: Question[];
  onComplete: (result: Test) => void;
  onClose: () => void;
}

type Phase =
  | 'permission'
  | 'ai-speaking'
  | 'user-answering'
  | 'submitting'
  | 'error';

const ANSWER_TIME = 30;

const CATEGORY_COLOR: Record<string, string> = {
  emotional: '#f87171',
  physical: '#fb923c',
  cognitive: '#60a5fa',
  behavioral: '#34d399',
  stressors: '#a78bfa',
};

const AssessmentLogo = ({ className = '' }: { className?: string }) => (
  <img
    src={stressLogo}
    alt="AI Stress Analyzer logo"
    className={`object-contain ${className}`}
    draggable={false}
  />
);

export default function VideoAssessmentModal({
  questions,
  onComplete,
  onClose,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRecorderRef = useRef<BrowserAudioFeatureRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const answerStartMsRef = useRef<number>(0);
  const answerDurationsRef = useRef<number[]>([]);
  const answerWordCountsRef = useRef<number[]>([]);
  const allResponsesRef = useRef<string[]>(Array(18).fill(''));
  const transcriptRef = useRef('');
  const fallbackRef = useRef('');
  const currentQRef = useRef(0);
  const advancingRef = useRef(false);

  const [phase, setPhase] = useState<Phase>('permission');
  const [currentQ, setCurrentQ] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [fallbackText, setFallbackText] = useState('');
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [timeLeft, setTimeLeft] = useState(ANSWER_TIME);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [error, setError] = useState('');
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) setSpeechSupported(false);
  }, []);

  useEffect(() => {
    if (videoRef.current && streamRef.current && !videoRef.current.srcObject) {
      videoRef.current.srcObject = streamRef.current;
    }
  });

  const requestPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      streamRef.current = stream;

      try {
        const recorder = new BrowserAudioFeatureRecorder();
        await recorder.init(stream);
        audioRecorderRef.current = recorder;
      } catch (recorderError) {
        console.warn(
          'Browser audio feature capture is unavailable:',
          recorderError
        );
        audioRecorderRef.current = null;
      }
      return true;
    } catch {
      setError(
        'Camera and microphone access is required for the video assessment. Please grant permission in your browser and try again.'
      );
      setPhase('error');
      return false;
    }
  };

  const speak = useCallback((text: string): Promise<void> => {
    return new Promise<void>((resolve) => {
      if (!('speechSynthesis' in window)) {
        resolve();
        return;
      }

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.87;
      utterance.pitch = 1;
      utterance.volume = 1;

      const pickVoice = () => {
        const voices = window.speechSynthesis.getVoices();
        const preferred =
          voices.find(
            (voice) =>
              voice.lang === 'en-US' &&
              /female|samantha|emma|victoria|karen/i.test(voice.name)
          ) ||
          voices.find((voice) => voice.lang === 'en-US') ||
          voices.find((voice) => voice.lang.startsWith('en'));
        if (preferred) utterance.voice = preferred;
      };

      if (window.speechSynthesis.getVoices().length === 0) {
        window.speechSynthesis.addEventListener('voiceschanged', pickVoice, {
          once: true,
        });
      } else {
        pickVoice();
      }

      utterance.onend = () => {
        setIsAISpeaking(false);
        resolve();
      };
      utterance.onerror = () => {
        setIsAISpeaking(false);
        resolve();
      };

      setIsAISpeaking(true);
      window.speechSynthesis.speak(utterance);
    });
  }, []);

  const startListening = useCallback(() => {
    transcriptRef.current = '';
    setTranscript('');
    answerStartMsRef.current = Date.now();
    audioRecorderRef.current?.startSegment();
    setIsRecording(true);
    setTimeLeft(ANSWER_TIME);

    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) {
      setSpeechSupported(false);
      return;
    }

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    let finalText = '';
    recognition.onresult = (event: any) => {
      let interim = '';
      for (
        let index = event.resultIndex;
        index < event.results.length;
        index += 1
      ) {
        if (event.results[index].isFinal) {
          finalText += `${event.results[index][0].transcript} `;
        } else {
          interim += event.results[index][0].transcript;
        }
      }

      const combined = (finalText + interim).trimStart();
      setTranscript(combined);
      transcriptRef.current = combined;
    };

    recognition.onerror = (event: any) => {
      if (
        event.error === 'not-allowed' ||
        event.error === 'service-not-allowed'
      ) {
        setSpeechSupported(false);
      }
    };

    try {
      recognition.start();
    } catch {
      // Ignore if recognition is already active.
    }
  }, []);

  const stopListening = useCallback(() => {
    audioRecorderRef.current?.stopSegment();
    setIsRecording(false);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore recognition stop failures.
      }
      recognitionRef.current = null;
    }
  }, []);

  const saveAndAdvance = useCallback(async () => {
    if (advancingRef.current) return;
    advancingRef.current = true;

    stopListening();
    window.speechSynthesis.cancel();

    const questionIndex = currentQRef.current;
    const answer =
      transcriptRef.current.trim() ||
      fallbackRef.current.trim() ||
      'no response';
    const elapsedMs = Math.max(
      1000,
      Date.now() - (answerStartMsRef.current || Date.now())
    );

    answerDurationsRef.current[questionIndex] = elapsedMs;
    answerWordCountsRef.current[questionIndex] = answer
      .split(/\s+/)
      .filter(Boolean).length;
    allResponsesRef.current[questionIndex] = answer;

    if (questionIndex < questions.length - 1) {
      const nextIndex = questionIndex + 1;
      currentQRef.current = nextIndex;
      setCurrentQ(nextIndex);
      transcriptRef.current = '';
      fallbackRef.current = '';
      setTranscript('');
      setFallbackText('');

      setPhase('ai-speaking');
      await speak(`Question ${nextIndex + 1}. ${questions[nextIndex].question}`);

      advancingRef.current = false;
      startListening();
      setPhase('user-answering');
      return;
    }

    setPhase('submitting');

    try {
      const totalWords = answerWordCountsRef.current.reduce(
        (sum, count) => sum + (count || 0),
        0
      );
      const totalMinutes =
        answerDurationsRef.current.reduce((sum, ms) => sum + (ms || 0), 0) /
        60000;
      const speakingRateWpm = totalMinutes > 0 ? totalWords / totalMinutes : 140;
      const negativeLexicon = [
        'sad',
        'depressed',
        'hopeless',
        'anxious',
        'worried',
        'angry',
        'overwhelmed',
        'tired',
        'panic',
        'fear',
        'stress',
        'crying',
        'hurt',
        'pain',
        'desperate',
      ];

      const joined = allResponsesRef.current.join(' ').toLowerCase();
      const negHits = negativeLexicon.reduce(
        (count, term) => count + (joined.includes(term) ? 1 : 0),
        0
      );
      const browserAudioFeatures =
        (await audioRecorderRef.current?.finalize({
          speaking_rate_wpm: speakingRateWpm,
          stress: Math.min(
            1,
            Math.max(0, Math.abs(speakingRateWpm - 140) / 80)
          ),
        })) ?? {
          speaking_rate_wpm: speakingRateWpm,
          stress: Math.min(
            1,
            Math.max(0, Math.abs(speakingRateWpm - 140) / 80)
          ),
        };

      const { data } = await api.post('/api/user/video-test/submit', {
        verbal_responses: allResponsesRef.current,
        audio_features: browserAudioFeatures,
        facial_features: { stress: 0.5 },
        sentiment_features: { negative: Math.min(1, negHits / 8) },
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
  }, [onComplete, questions, speak, startListening, stopListening]);

  const startAssignment = useCallback(async () => {
    if (questions.length === 0) {
      setError(
        'Questions are still loading. Please close this window and try again.'
      );
      setPhase('error');
      return;
    }

    currentQRef.current = 0;
    advancingRef.current = false;
    setCurrentQ(0);
    setPhase('ai-speaking');

    await speak(
      'Hello! This is your AI Stress Assignment. I will ask you 18 questions about your current stress levels. Please answer each question naturally and honestly. Let us begin.'
    );

    setTranscript('');
    setFallbackText('');
    transcriptRef.current = '';
    fallbackRef.current = '';

    await speak(`Question 1. ${questions[0].question}`);
    startListening();
    setPhase('user-answering');
  }, [questions, speak, startListening]);

  const handleStartVideoAssessment = async () => {
    if (isStarting) return;
    setIsStarting(true);
    try {
      const granted = await requestPermissions();
      if (!granted) return;
      await startAssignment();
    } finally {
      setIsStarting(false);
    }
  };

  useEffect(() => {
    if (!isRecording) return undefined;
    if (timeLeft <= 0) {
      void saveAndAdvance();
      return undefined;
    }

    const timer = setInterval(() => setTimeLeft((seconds) => seconds - 1), 1000);
    return () => clearInterval(timer);
  }, [isRecording, saveAndAdvance, timeLeft]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      void audioRecorderRef.current?.dispose();
      window.speechSynthesis.cancel();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore recognition stop failures.
        }
      }
    };
  }, []);

  const questionTotal = Math.max(questions.length, 1);
  const currentQuestion = questions[currentQ];
  const categoryLabel = currentQuestion
    ? `${currentQuestion.category.charAt(0).toUpperCase()}${currentQuestion.category.slice(1)}`
    : 'Assessment';
  const categoryColor = currentQuestion
    ? CATEGORY_COLOR[currentQuestion.category] ?? '#60a5fa'
    : '#60a5fa';
  const isLive = phase === 'ai-speaking' || phase === 'user-answering';
  const progress =
    phase === 'submitting'
      ? 100
      : Math.round(
          ((phase === 'user-answering' ? currentQ + 1 : currentQ) / questionTotal) *
            100
        );
  const statusText = isAISpeaking
    ? 'AI is speaking'
    : isRecording
      ? 'Listening to your answer'
      : 'Preparing next step';
  const permissionSteps = [
    {
      title: 'Click the start button',
      text: 'Use the highlighted button below to launch the video assessment.',
    },
    {
      title: 'Allow camera and microphone',
      text: 'Your browser permission popup appears immediately after that click.',
    },
    {
      title: 'Begin Question 1',
      text: 'As soon as access is granted, the first question starts automatically.',
    },
  ];
  const readinessTips = [
    'Find a quiet space with minimal background noise.',
    'Keep your face centered and visible on screen.',
    'Answer naturally in your normal speaking voice.',
  ];

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-900 px-4 py-3 md:px-6">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/95 p-1.5 shadow-sm shadow-black/20">
              <AssessmentLogo className="h-full w-full" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">
                AI Stress Assignment
              </p>
              <p className="truncate text-xs text-slate-400">
                Simple video assessment flow
              </p>
            </div>
          </div>

          {phase !== 'submitting' && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </header>

      {isLive && (
        <div className="h-1 bg-slate-800">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-auto">
        {phase === 'permission' && (
          <div className="flex flex-1 items-center justify-center p-6 md:p-8">
            <div className="w-full max-w-6xl overflow-hidden rounded-[2rem] border border-slate-800 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.16),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(139,92,246,0.12),transparent_34%),linear-gradient(180deg,#0f172a_0%,#111827_100%)] shadow-2xl shadow-black/40">
              <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
                <section className="relative overflow-hidden border-b border-slate-800 p-6 md:p-8 lg:border-b-0 lg:border-r">
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.08),transparent_26%),radial-gradient(circle_at_70%_80%,rgba(99,102,241,0.1),transparent_30%)]" />
                  <div className="relative">
                    <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
                      <Sparkles className="h-4 w-4" />
                      AI Stress Assignment
                    </div>

                    <div className="mt-6 flex flex-col gap-5 md:flex-row md:items-center">
                      <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-[1.75rem] bg-white/95 p-3 shadow-xl shadow-blue-950/30">
                        <AssessmentLogo className="h-full w-full" />
                      </div>
                      <div className="max-w-2xl">
                        <h2 className="text-3xl font-bold text-white md:text-4xl">
                          Understand your stress through a guided video session
                        </h2>
                        <p className="mt-4 text-base leading-8 text-slate-300">
                          Start with one clear click, allow camera and microphone
                          access, and the assessment begins right away. The flow is
                          designed to feel calm, guided, and easy to follow.
                        </p>
                      </div>
                    </div>

                    <div className="mt-8 grid gap-4 sm:grid-cols-3">
                      {[
                        {
                          icon: <Mic className="h-5 w-5 text-sky-300" />,
                          title: 'Voice patterns',
                          text: 'Listens to how you answer each guided question.',
                        },
                        {
                          icon: <Video className="h-5 w-5 text-violet-300" />,
                          title: 'Live session',
                          text: 'Uses camera and microphone during the assessment.',
                        },
                        {
                          icon: <ShieldCheck className="h-5 w-5 text-emerald-300" />,
                          title: 'Private flow',
                          text: 'Built for a secure and guided experience.',
                        },
                      ].map((item) => (
                        <div
                          key={item.title}
                          className="rounded-[1.5rem] border border-slate-800/90 bg-slate-900/70 p-4 backdrop-blur-sm"
                        >
                          <div className="mb-3 inline-flex rounded-2xl bg-slate-950/80 p-2.5 shadow-lg shadow-black/20">
                            {item.icon}
                          </div>
                          <p className="font-semibold text-white">{item.title}</p>
                          <p className="mt-1 text-sm leading-6 text-slate-400">
                            {item.text}
                          </p>
                        </div>
                      ))}
                    </div>

                    <div className="mt-8 rounded-[1.75rem] border border-slate-800/90 bg-slate-950/45 p-5 backdrop-blur-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                        Set yourself up
                      </p>
                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        {readinessTips.map((tip) => (
                          <div
                            key={tip}
                            className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
                          >
                            <div className="mb-3 h-2.5 w-2.5 rounded-full bg-blue-400 shadow-[0_0_14px_rgba(96,165,250,0.8)]" />
                            <p className="text-sm leading-6 text-slate-300">{tip}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="relative p-6 md:p-8">
                  <div className="absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.15),transparent_70%)]" />
                  <div className="relative">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                      How it works
                    </p>
                    <h3 className="mt-3 text-2xl font-bold text-white">
                      Start here
                    </h3>
                    <p className="mt-3 max-w-xl text-sm leading-7 text-slate-300">
                      The highlighted button below is the first thing to click.
                      Right after that, your browser asks for permission and the
                      video assessment starts automatically.
                    </p>

                    <div className="mt-6 rounded-[1.75rem] border border-blue-500/25 bg-[linear-gradient(180deg,rgba(37,99,235,0.2),rgba(30,41,59,0.82))] p-5 shadow-[0_20px_60px_rgba(37,99,235,0.18)]">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="inline-flex animate-float items-center gap-2 rounded-full border border-blue-300/20 bg-blue-400/15 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-blue-100">
                          <ChevronRight className="h-4 w-4 rotate-90" />
                          Click here first
                        </div>
                        <div className="rounded-full border border-white/10 bg-slate-950/45 px-3 py-1 text-xs text-slate-200">
                          Takes about 15 minutes
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950/55 px-3 py-1.5 text-xs font-medium text-slate-200">
                          <Camera className="h-3.5 w-3.5 text-emerald-300" />
                          Camera required
                        </div>
                        <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950/55 px-3 py-1.5 text-xs font-medium text-slate-200">
                          <Mic className="h-3.5 w-3.5 text-sky-300" />
                          Microphone required
                        </div>
                        <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950/55 px-3 py-1.5 text-xs font-medium text-slate-200">
                          <Video className="h-3.5 w-3.5 text-violet-300" />
                          Starts instantly
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={handleStartVideoAssessment}
                        disabled={isStarting}
                        aria-describedby="permission-start-note"
                        className="btn-glow animate-glowPulse group relative mt-5 inline-flex w-full items-center justify-between gap-4 rounded-[1.35rem] border border-white/10 bg-[linear-gradient(135deg,#2563eb,#4338ca_58%,#4f46e5)] px-6 py-4 text-left text-base font-semibold text-white shadow-[0_20px_50px_rgba(37,99,235,0.35)] transition hover:-translate-y-0.5 hover:shadow-[0_24px_65px_rgba(37,99,235,0.45)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-300/30 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        <span className="flex items-center gap-3">
                          <span className="relative flex h-3 w-3">
                            {!isStarting && (
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-300/75" />
                            )}
                            <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
                          </span>
                          <span>
                            {isStarting
                              ? 'Starting assessment...'
                              : 'Start Video Assessment'}
                          </span>
                        </span>

                        <span className="inline-flex items-center gap-2 text-sm text-blue-50/90">
                          <span>Open camera + mic</span>
                          {isStarting ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <ChevronRight className="h-5 w-5 transition group-hover:translate-x-1" />
                          )}
                        </span>
                      </button>

                      <p
                        id="permission-start-note"
                        className="mt-3 text-sm leading-6 text-blue-100/85"
                      >
                        The browser permission popup appears immediately after
                        you click the button above.
                      </p>
                    </div>

                    <div className="mt-6">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        What happens next
                      </p>
                      <div className="mt-4 space-y-3">
                        {permissionSteps.map((step, index) => (
                          <div
                            key={step.title}
                            className={`flex items-start gap-3 rounded-[1.35rem] border p-4 ${
                              index === 0
                                ? 'border-blue-500/25 bg-blue-500/10 shadow-lg shadow-blue-950/10'
                                : 'border-slate-800 bg-slate-800/60'
                            }`}
                          >
                            <div
                              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl text-sm font-semibold ${
                                index === 0
                                  ? 'bg-blue-500/20 text-blue-100'
                                  : 'bg-slate-900 text-slate-200'
                              }`}
                            >
                              {index + 1}
                            </div>
                            <div>
                              <p className="text-sm font-semibold text-white">
                                {step.title}
                              </p>
                              <p className="mt-1 text-sm leading-6 text-slate-300">
                                {step.text}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="mt-6 rounded-[1.75rem] border border-slate-700/80 bg-slate-800/55 p-5">
                      <div className="flex items-start gap-4">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/15">
                          <Camera className="h-5 w-5 text-emerald-300" />
                        </div>
                        <div>
                          <p className="text-base font-semibold text-white">
                            Before you start
                          </p>
                          <p className="mt-2 text-sm leading-6 text-slate-400">
                            Sit in a quiet place, keep your face visible, and
                            answer naturally in your own words.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}

        {isLive && (
          <div className="flex flex-1 items-center justify-center p-4 md:p-6">
            <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-2">
              <aside className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
                <div className="relative overflow-hidden rounded-2xl bg-slate-950 aspect-[4/5] md:aspect-video lg:min-h-[520px] lg:aspect-auto">
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    playsInline
                    className="h-full w-full object-cover"
                    style={{ transform: 'scaleX(-1)' }}
                  />
                  <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.08)_0%,rgba(15,23,42,0.16)_35%,rgba(2,6,23,0.78)_100%)]" />
                  <div className="absolute left-3 top-3 rounded-full bg-black/65 px-3 py-1 text-xs text-white">
                    {isRecording ? 'Recording' : 'Camera on'}
                  </div>
                  <div className="absolute bottom-3 left-3 rounded-lg bg-black/60 px-3 py-1 text-xs text-white">
                    You
                  </div>
                </div>

                <div className="mt-4 space-y-3">
                  {[
                    'Keep your face visible in the camera on the left.',
                    'Read the question on the right, then answer naturally.',
                    'Click Next when you are ready to continue.',
                  ].map((tip, index) => (
                    <div
                      key={tip}
                      className="flex items-start gap-3 rounded-2xl border border-slate-800 bg-slate-800/50 p-4"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-600/20 text-xs font-semibold text-blue-200">
                        {index + 1}
                      </div>
                      <p className="text-sm leading-6 text-slate-200">{tip}</p>
                    </div>
                  ))}
                </div>
              </aside>

              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5 md:p-6">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-400">
                      Question <span className="font-bold text-white">{currentQ + 1}</span> of{' '}
                      {questionTotal}
                    </p>
                    <p className="mt-1 text-sm text-slate-300">{statusText}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <div
                      className="rounded-full border px-3 py-1.5 text-xs font-medium"
                      style={{
                        borderColor: `${categoryColor}55`,
                        background: `${categoryColor}18`,
                        color: categoryColor,
                      }}
                    >
                      {categoryLabel}
                    </div>
                    <div className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300">
                      {timeLeft}s left
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-800/60 p-5">
                  <div className="mb-3 flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/95 p-1.5 shadow-md shadow-black/20">
                      <AssessmentLogo className="h-full w-full" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">AI guide</p>
                      <p className="text-sm text-slate-400">{statusText}</p>
                    </div>
                  </div>
                  <p
                    className="text-[11px] font-semibold uppercase tracking-[0.2em]"
                    style={{ color: categoryColor }}
                  >
                    {currentQuestion?.category || 'Question'}
                  </p>
                  <p className="mt-3 text-lg font-medium leading-8 text-white md:text-[1.35rem]">
                    {currentQuestion?.question}
                  </p>
                </div>

                <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-800/50 p-5">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-white">Your answer</p>
                    <div className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs text-slate-300">
                      {speechSupported ? 'Speech recognition on' : 'Typing mode'}
                    </div>
                  </div>

                  <div className="min-h-[150px] rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                    {transcript ? (
                      <p className="text-sm leading-7 text-white">{transcript}</p>
                    ) : speechSupported ? (
                      <p className="text-sm italic leading-7 text-slate-400">
                        Wait for the AI to finish, then speak naturally. Your answer will appear here.
                      </p>
                    ) : (
                      <p className="text-sm italic leading-7 text-slate-400">
                        Voice recognition is unavailable in this browser, so please type your answer below.
                      </p>
                    )}
                  </div>

                  {!speechSupported && (
                    <textarea
                      value={fallbackText}
                      onChange={(event) => {
                        setFallbackText(event.target.value);
                        fallbackRef.current = event.target.value;
                      }}
                      placeholder='Type your answer, for example: "sometimes", "often", "rarely", or explain it in your own words."'
                      rows={3}
                      className="mt-4 w-full resize-none rounded-2xl border border-slate-700 bg-slate-800 p-4 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                    />
                  )}
                </div>

                {phase === 'user-answering' && (
                  <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center">
                    <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/60 px-4 py-2 text-sm text-slate-300">
                      {isRecording ? (
                        <>
                          <Mic className="h-4 w-4 animate-pulse text-rose-300" />
                          Recording answer
                        </>
                      ) : (
                        <>
                          <MicOff className="h-4 w-4 text-slate-400" />
                          Waiting for next prompt
                        </>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={saveAndAdvance}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 md:ml-auto"
                    >
                      {currentQ < questions.length - 1
                        ? 'Next Question'
                        : 'Finish Assessment'}
                      {currentQ < questions.length - 1 ? (
                        <ChevronRight className="h-4 w-4" />
                      ) : (
                        <ShieldCheck className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                )}
              </section>
            </div>
          </div>
        )}

        {phase === 'submitting' && (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900 p-8 text-center">
              <div className="mx-auto mb-5 flex h-24 w-24 items-center justify-center rounded-[1.75rem] bg-white/95 p-3 shadow-xl shadow-blue-950/30">
                <AssessmentLogo className="h-full w-full" />
              </div>
              <Loader2 className="mx-auto h-10 w-10 animate-spin text-blue-300" />
              <h2 className="mt-5 text-3xl font-bold text-white">
                Analyzing your assessment
              </h2>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                We are processing your responses and preparing your result.
              </p>
            </div>
          </div>
        )}

        {phase === 'error' && (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900 p-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-rose-500/15">
                <X className="h-8 w-8 text-rose-300" />
              </div>
              <h2 className="text-2xl font-bold text-white">Assessment Error</h2>
              <p className="mt-3 text-sm leading-7 text-slate-300">{error}</p>
              <button
                type="button"
                onClick={onClose}
                className="mt-6 rounded-2xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-500"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
