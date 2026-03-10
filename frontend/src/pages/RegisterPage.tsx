import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { User, Mail, Lock, Briefcase, FileCheck, ArrowRight, AlertCircle, CheckCircle, MapPin, Calendar, Users, Upload, Phone } from 'lucide-react';
import stressLogo from '../../assets/stress logo.png';

const RegisterPage = () => {
  const navigate = useNavigate();
  const [stateMedicalCouncils, setStateMedicalCouncils] = useState<string[]>([]);
  const [userType, setUserType] = useState<'user' | 'doctor'>('user');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    // User-specific fields
    age: '',
    gender: '',
    location: '',
    hasPreviousStressIssues: false,
    medicalDocument: null as File | null,
    // Doctor-specific fields
    licenseNumber: '',
    stateMedicalCouncil: '',
    specialization: '',
    // SMS
    phone_number: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const loadStateMedicalCouncils = async () => {
      try {
        const councils = await authService.getStateMedicalCouncils();
        setStateMedicalCouncils(councils);
      } catch (err) {
        console.error('Failed to load state medical councils', err);
      }
    };
    loadStateMedicalCouncils();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData({ ...formData, [name]: checked });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    
    // Validate file size (10MB max)
    if (file && file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 
                          'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (file && !allowedTypes.includes(file.type)) {
      setError('Only PDF, JPG, PNG, DOC, and DOCX files are allowed');
      return;
    }
    
    setFormData({ ...formData, medicalDocument: file });
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    // Phone number validation (optional but must be valid if provided)
    if (formData.phone_number && !/^\+[1-9]\d{6,14}$/.test(formData.phone_number.trim())) {
      setError('Phone number must be in international format e.g. +919876543210');
      return;
    }

    // User-specific validation
    if (userType === 'user') {
      if (!formData.age || parseInt(formData.age) < 13 || parseInt(formData.age) > 120) {
        setError('Age must be between 13 and 120');
        return;
      }
      if (!formData.gender) {
        setError('Please select your gender');
        return;
      }
      if (!formData.location || formData.location.trim().length < 2) {
        setError('Please enter your location');
        return;
      }
    }

    // Doctor-specific validation
    if (userType === 'doctor') {
      if (!formData.licenseNumber || !formData.specialization || !formData.stateMedicalCouncil) {
        setError('License number, state medical council, and specialization are required for doctors');
        return;
      }
    }

    setLoading(true);

    try {
      if (userType === 'user') {
        // Register user
        await authService.registerUser(
          formData.name,
          formData.email,
          formData.password,
          parseInt(formData.age),
          formData.gender,
          formData.location,
          formData.hasPreviousStressIssues,
          formData.phone_number.trim() || undefined
        );
        
        // Upload medical document if provided
        if (formData.medicalDocument) {
          await authService.uploadMedicalDocument(formData.medicalDocument);
        }
      } else {
        // Register doctor
        await authService.registerDoctor(
          formData.name,
          formData.email,
          formData.password,
          formData.licenseNumber,
          formData.stateMedicalCouncil,
          formData.specialization,
          ['Mon 9:00-10:00', 'Wed 14:00-15:00', 'Fri 11:00-12:00'],
          formData.phone_number.trim() || undefined
        );
      }

      setSuccess(true);
      setError('');
      
      // Redirect to OTP verification page
      setTimeout(() => {
        navigate('/verify-otp', { 
          state: { 
            email: formData.email,
            message: 'Please check your email for the verification code.'
          } 
        });
      }, 1500);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center">
          <div className="inline-flex items-center justify-center bg-green-100 p-4 rounded-full mb-4">
            <CheckCircle className="w-16 h-16 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Registration Successful!</h2>
          <p className="text-gray-600 mb-4">
            We've sent a verification code to <strong>{formData.email}</strong>
            {formData.phone_number && <> and an SMS message to <strong>{formData.phone_number}</strong></>}
          </p>
          <p className="text-sm text-gray-500">
            Please check your email (and SMS if provided) for the 6-digit verification code.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Redirecting to verification page...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center ">
            <img
              src={stressLogo}
              alt="AI Stress Detector Logo"
              className="w-10 h-10 object-contain"
            />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Create Account
          </h1>
          <p className="text-gray-600">Join thousands improving their mental health</p>
        </div>

        {/* Registration Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
          {/* User Type Selection */}
          <div className="grid grid-cols-2 gap-4 mb-8 p-1 bg-gray-100 rounded-xl">
            <button
              type="button"
              onClick={() => setUserType('user')}
              className={`flex items-center justify-center space-x-2 py-3.5 px-6 rounded-lg font-semibold transition-all duration-300 ${
                userType === 'user'
                  ? 'bg-white text-blue-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <User className="w-5 h-5" />
              <span>User/Patient</span>
            </button>
            <button
              type="button"
              onClick={() => setUserType('doctor')}
              className={`flex items-center justify-center space-x-2 py-3.5 px-6 rounded-lg font-semibold transition-all duration-300 ${
                userType === 'doctor'
                  ? 'bg-white text-purple-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Briefcase className="w-5 h-5" />
              <span>Doctor</span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Basic Information */}
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Full Name *
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                    placeholder="John Doe"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Email Address *
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                    placeholder="your@email.com"
                  />
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Password *
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Confirm Password *
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            {/* SMS Phone Number — shown for both user and doctor */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                SMS Phone Number <span className="text-gray-400 font-normal">(Optional)</span>
              </label>
              <div className="relative">
                <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="tel"
                  name="phone_number"
                  value={formData.phone_number}
                  onChange={handleChange}
                  className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all outline-none"
                  placeholder="+919876543210"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1.5 ml-1 flex items-center gap-1">
                <span className="text-green-600">💬</span>
                Include country code (e.g. +91 for India). Used to send appointment updates &amp; stress results via SMS.
              </p>
            </div>

            {/* User-specific fields */}
            {userType === 'user' && (
              <div className="pt-5 border-t border-gray-200 space-y-4">
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-4">
                  <p className="text-sm text-blue-700 flex items-center">
                    <User className="w-4 h-4 mr-2" />
                    Additional information for better personalized care
                  </p>
                </div>

                <div className="grid md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Age *
                    </label>
                    <div className="relative">
                      <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="number"
                        name="age"
                        value={formData.age}
                        onChange={handleChange}
                        required={userType === 'user'}
                        min="13"
                        max="120"
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                        placeholder="25"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Gender *
                    </label>
                    <div className="relative">
                      <Users className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <select
                        name="gender"
                        value={formData.gender}
                        onChange={handleChange}
                        required={userType === 'user'}
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none appearance-none"
                      >
                        <option value="">Select</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                        <option value="Prefer not to say">Prefer not to say</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Location *
                    </label>
                    <div className="relative">
                      <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        name="location"
                        value={formData.location}
                        onChange={handleChange}
                        required={userType === 'user'}
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                        placeholder="New York"
                      />
                    </div>
                  </div>
                </div>

                {/* Medical History */}
                <div className="space-y-3">
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      name="hasPreviousStressIssues"
                      checked={formData.hasPreviousStressIssues}
                      onChange={handleChange}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label className="text-sm text-gray-700">
                      I have previous stress-related medical history
                    </label>
                  </div>

                  {formData.hasPreviousStressIssues && (
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Upload Medical Document (Optional)
                      </label>
                      <div className="relative">
                        <Upload className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                          type="file"
                          onChange={handleFileChange}
                          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1.5 ml-1">
                        Accepted formats: PDF, JPG, PNG, DOC, DOCX (Max 10MB)
                      </p>
                      {formData.medicalDocument && (
                        <p className="text-sm text-green-600 mt-2">
                          ✓ {formData.medicalDocument.name}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Doctor-specific fields */}
            {userType === 'doctor' && (
              <div className="pt-5 border-t border-gray-200 space-y-4">
                <div className="bg-purple-50 border border-purple-100 rounded-xl p-4 mb-4">
                  <p className="text-sm text-purple-700 flex items-center">
                    <FileCheck className="w-4 h-4 mr-2" />
                    Additional information required for doctors
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      License Number *
                    </label>
                    <div className="relative">
                      <FileCheck className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        name="licenseNumber"
                        value={formData.licenseNumber}
                        onChange={handleChange}
                        required={userType === 'doctor'}
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                        placeholder="DMC/R/12345"
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1.5 ml-1">
                      Use your registration number as listed in IMR
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      State Medical Council *
                    </label>
                    <div className="relative">
                      <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <select
                        name="stateMedicalCouncil"
                        value={formData.stateMedicalCouncil}
                        onChange={handleChange}
                        required={userType === 'doctor'}
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none appearance-none"
                      >
                        <option value="">Select council</option>
                        {stateMedicalCouncils.map((council) => (
                          <option key={council} value={council}>
                            {council}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Specialization *
                    </label>
                    <div className="relative">
                      <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        name="specialization"
                        value={formData.specialization}
                        onChange={handleChange}
                        required={userType === 'doctor'}
                        className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
                        placeholder="Clinical Psychology"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-start space-x-2 text-sm text-gray-600 pt-2">
              <input type="checkbox" required className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span>
                I agree to the <a href="#" className="text-blue-600 hover:text-blue-700 font-medium">Terms of Service</a> and{' '}
                <a href="#" className="text-blue-600 hover:text-blue-700 font-medium">Privacy Policy</a>
              </span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 mt-6"
            >
              <span>{loading ? 'Creating Account...' : 'Create Account'}</span>
              {!loading && (
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Already have an account?{' '}
              <button
                onClick={() => navigate('/login')}
                className="text-blue-600 hover:text-blue-700 font-semibold"
              >
                Sign in here
              </button>
            </p>
          </div>

          <div className="mt-4 text-center">
            <button
              onClick={() => navigate('/')}
              className="text-gray-500 hover:text-gray-700 text-sm flex items-center justify-center mx-auto space-x-1"
            >
              <span>←</span>
              <span>Back to Home</span>
            </button>
          </div>
        </div>

        {/* Trust Indicators */}
        <div className="mt-6 flex items-center justify-center space-x-8 text-xs text-gray-500">
          <div className="flex items-center space-x-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>Email Verified</span>
          </div>
          <div className="flex items-center space-x-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>HIPAA Compliant</span>
          </div>
          <div className="flex items-center space-x-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>Secure & Private</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
