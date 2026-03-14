import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mail, Lock, ArrowLeft, ArrowRight, CheckCircle,
  AlertCircle, Eye, EyeOff, Shield, RefreshCw
} from 'lucide-react';
import api from '../services/api';
import stressLogo from '../../assets/stress logo.png';

type Step = 'email' | 'otp' | 'password' | 'success';

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('email');

  // Email step
  const [email, setEmail] = useState('');
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailError, setEmailError] = useState('');

  // OTP step
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState('');
  const [timeLeft, setTimeLeft] = useState(600);
  const [resending, setResending] = useState(false);
  // ✅ FIX 2: Stable ref array — initialized once, never recreated
  const otpRefs = useRef<Array<HTMLInputElement | null>>([null, null, null, null, null, null]);

  // Password step
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');

  // Countdown timer
  useEffect(() => {
    if (step !== 'otp' || timeLeft <= 0) return;
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000);
    return () => clearInterval(timer);
  }, [step, timeLeft]);

  // ✅ FIX 2: Auto-focus first OTP box when step changes to otp
  useEffect(() => {
    if (step === 'otp') {
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    }
  }, [step]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  // ── Step 1: Send OTP ──────────────────────────────────────────────
  const handleSendOtp = async () => {
    setEmailError('');
    if (!email.trim()) { setEmailError('Please enter your email address'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError('Please enter a valid email address'); return;
    }
    setEmailLoading(true);
    try {
      await api.post('/api/auth/forgot-password', { email });
      setTimeLeft(600);
      setOtp(['', '', '', '', '', '']);
      setStep('otp');
    } catch (err: any) {
      setEmailError(err.response?.data?.detail || 'Failed to send reset code. Please try again.');
    } finally {
      setEmailLoading(false);
    }
  };

  // ✅ FIX 2: Correct cursor auto-advance on digit entry
  const handleOtpChange = useCallback((index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value.slice(-1);
    setOtp(newOtp);
    // Auto move to next box
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  }, [otp]);

  // ✅ FIX 2: Backspace goes to previous box, arrow keys navigate
  const handleOtpKeyDown = useCallback((index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (otp[index]) {
        const newOtp = [...otp];
        newOtp[index] = '';
        setOtp(newOtp);
      } else if (index > 0) {
        otpRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      otpRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  }, [otp]);

  // ✅ FIX 2: Paste support — fills all 6 boxes at once
  const handleOtpPaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    const newOtp = ['', '', '', '', '', ''];
    pasted.split('').forEach((char, i) => { newOtp[i] = char; });
    setOtp(newOtp);
    otpRefs.current[Math.min(pasted.length, 5)]?.focus();
  }, []);

  // ── Step 2: Verify OTP ────────────────────────────────────────────
  const handleVerifyOtp = async () => {
    setOtpError('');
    const code = otp.join('');
    if (code.length !== 6) { setOtpError('Please enter the complete 6-digit code'); return; }
    setOtpLoading(true);
    try {
      await api.post('/api/auth/verify-reset-otp', { email, otp: code });
      setStep('password');
    } catch (err: any) {
      setOtpError(err.response?.data?.detail || 'Invalid or expired code. Please try again.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setResending(true);
    setOtpError('');
    try {
      await api.post('/api/auth/forgot-password', { email });
      setTimeLeft(600);
      setOtp(['', '', '', '', '', '']);
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch (err: any) {
      setOtpError('Failed to resend code. Please try again.');
    } finally {
      setResending(false);
    }
  };

  // ── Step 3: Reset Password ────────────────────────────────────────
  // ✅ FIX 3: YES — backend /api/auth/reset-password updates password in MongoDB
  // The backend hashes the new password with bcrypt and calls collection.update_one()
  const handleResetPassword = async () => {
    setPwError('');
    if (newPassword.length < 8) { setPwError('Password must be at least 8 characters long'); return; }
    if (newPassword !== confirmPassword) { setPwError('Passwords do not match'); return; }
    setPwLoading(true);
    try {
      await api.post('/api/auth/reset-password', {
        email,
        otp: otp.join(''),
        new_password: newPassword,
      });
      setStep('success');
    } catch (err: any) {
      setPwError(err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setPwLoading(false);
    }
  };

  // ✅ FIX 1: All steps rendered in ONE single return
  // Previously, the Wrapper component was defined INSIDE the render function.
  // React saw it as a NEW component type every render → unmounted + remounted
  // the entire tree → lost router context → redirected to login.
  // Fix: use conditional rendering with {step === 'x' && (...)} instead.
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full">

        {/* Shared logo header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-3">
            <img src={stressLogo} alt="Logo" className="w-10 h-10 object-contain" />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-1">
            Welcome Back
          </h1>
          <p className="text-gray-500 text-sm">Sign in to continue your mental health journey</p>
        </div>

        {/* ── Step 1: Email ───────────────────────────────────────── */}
        {step === 'email' && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center">
                <Mail className="w-8 h-8 text-blue-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 text-center mb-1">Forgot Password?</h2>
            <p className="text-gray-500 text-sm text-center mb-6">
              No worries! Enter your email and we'll send you a reset code.
            </p>

            {emailError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start space-x-2 mb-4">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{emailError}</p>
              </div>
            )}

            <div className="mb-5">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSendOtp()}
                  className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                  placeholder="john@example.com"
                  autoFocus
                />
              </div>
            </div>

            <button
              onClick={handleSendOtp}
              disabled={emailLoading}
              className="group w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold shadow-lg disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              <Mail className="w-5 h-5" />
              <span>{emailLoading ? 'Sending...' : 'Send Reset Code'}</span>
              {!emailLoading && <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />}
            </button>

            <button
              onClick={() => navigate('/login')}
              className="mt-4 w-full text-gray-500 hover:text-gray-700 text-sm flex items-center justify-center space-x-1 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Sign In</span>
            </button>
          </div>
        )}

        {/* ── Step 2: OTP ─────────────────────────────────────────── */}
        {step === 'otp' && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center">
                <Shield className="w-8 h-8 text-green-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 text-center mb-1">Verify Your Email</h2>
            <p className="text-gray-500 text-sm text-center mb-1">We sent a 6-digit code to</p>
            <p className="text-gray-800 font-semibold text-center mb-6">{email}</p>

            {otpError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start space-x-2 mb-4">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{otpError}</p>
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-3">Verification Code</label>
              <div className="flex gap-2 justify-between">
                {otp.map((digit, i) => (
                  <input
                    key={i}
                    ref={el => { otpRefs.current[i] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={e => handleOtpChange(i, e.target.value)}
                    onKeyDown={e => handleOtpKeyDown(i, e)}
                    onPaste={i === 0 ? handleOtpPaste : undefined}
                    className="w-12 h-12 text-center text-xl font-bold border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
                  />
                ))}
              </div>
            </div>

            {/* Timer */}
            <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center justify-center space-x-2 mb-5">
              <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/>
              </svg>
              {timeLeft > 0 ? (
                <p className="text-sm text-gray-600">
                  Code expires in <span className="font-bold text-gray-900">{formatTime(timeLeft)}</span>
                </p>
              ) : (
                <p className="text-sm text-red-600 font-semibold">Code expired — please resend</p>
              )}
            </div>

            <button
              onClick={handleVerifyOtp}
              disabled={otpLoading || otp.join('').length !== 6}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold shadow-lg disabled:opacity-50 flex items-center justify-center space-x-2 mb-3"
            >
              <Shield className="w-5 h-5" />
              <span>{otpLoading ? 'Verifying...' : 'Verify Code'}</span>
            </button>

            <div className="text-center mb-3">
              <span className="text-sm text-gray-500">Didn't receive it? </span>
              <button
                onClick={handleResendOtp}
                disabled={resending || timeLeft > 540}
                className="text-sm font-semibold text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed inline-flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${resending ? 'animate-spin' : ''}`} />
                {resending ? 'Resending...' : timeLeft > 540 ? `Resend in ${timeLeft - 540}s` : 'Resend Code'}
              </button>
            </div>

            <button
              onClick={() => setStep('email')}
              className="w-full text-gray-500 hover:text-gray-700 text-sm flex items-center justify-center space-x-1 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
          </div>
        )}

        {/* ── Step 3: New Password ─────────────────────────────────── */}
        {step === 'password' && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center">
                <Lock className="w-8 h-8 text-blue-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 text-center mb-1">Create New Password</h2>
            <p className="text-gray-500 text-sm text-center mb-6">
              Choose a strong password to secure your account.
            </p>

            {pwError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start space-x-2 mb-4">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{pwError}</p>
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">New Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showNew ? 'text' : 'password'}
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  autoFocus
                  className="w-full pl-12 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                  placeholder="Enter new password"
                />
                <button type="button" onClick={() => setShowNew(!showNew)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showNew ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showConfirm ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleResetPassword()}
                  className="w-full pl-12 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                  placeholder="Confirm new password"
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showConfirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="bg-blue-50 rounded-xl px-4 py-2.5 mb-5">
              <p className="text-sm text-blue-700">Password must be at least 8 characters long</p>
            </div>

            <button
              onClick={handleResetPassword}
              disabled={pwLoading}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold shadow-lg disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              <Lock className="w-5 h-5" />
              <span>{pwLoading ? 'Resetting...' : 'Reset Password'}</span>
            </button>
          </div>
        )}

        {/* ── Step 4: Success ──────────────────────────────────────── */}
        {step === 'success' && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100 text-center">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Password Reset!</h2>
            <p className="text-gray-500 text-sm mb-6">
              Your password has been successfully updated. You can now sign in with your new password.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold shadow-lg flex items-center justify-center space-x-2"
            >
              <span>Go to Sign In</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        )}

      </div>
    </div>
  );
};

export default ForgotPasswordPage;