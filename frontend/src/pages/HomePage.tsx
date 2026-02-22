import { useNavigate } from 'react-router-dom';
import { Brain, Heart, Stethoscope, Users, Shield, TrendingUp, Activity, TestTube, Phone, Pill, MapPin, ExternalLink, Youtube } from 'lucide-react';
import stressLogo from '../../assets/stress logo.png';

const HomePage = () => {
  const navigate = useNavigate();

  const services = [
    {
      icon: Heart,
      title: "Cognitive-Behavioral Therapy",
      description: "Regular health checks can identify any early signs of health issues.",
      action: () => window.open('https://youtube.com/playlist?list=PL4Qw4-tlRJe-sZ_U4Fzi66UXMGvkPTf7P&si=RzYb3Up18ipCmRbN', '_blank'),
      buttonText: "Watch CBT Videos",
      buttonIcon: Youtube,
      color: "blue"
    },
    {
      icon: TestTube,
      title: "Blood Test",
      description: "Our Website also provides the Blood Test Laboratory. A blood test is one of the most common tests healthcare providers use to monitor your overall health or help diagnose medical conditions.",
      action: () => {
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              const lat = position.coords.latitude;
              const lng = position.coords.longitude;
              window.open(`https://www.google.com/maps/search/pathology+lab+near+me/@${lat},${lng},15z`, '_blank');
            },
            () => {
              window.open('https://www.google.com/maps/search/pathology+lab+near+me', '_blank');
            }
          );
        } else {
          window.open('https://www.google.com/maps/search/pathology+lab+near+me', '_blank');
        }
      },
      buttonText: "Find Nearby Labs",
      buttonIcon: MapPin,
      color: "green"
    },
    {
      icon: Phone,
      title: "EMERGENCY",
      description: "Emergency Ambulance Numbers - Call immediately in case of medical emergency",
      action: () => {
        if (confirm('Call emergency ambulance service 101?')) {
          window.location.href = 'tel:101';
        }
      },
      buttonText: "Call 101",
      buttonIcon: Phone,
      color: "red"
    },
    {
      icon: Pill,
      title: "Medicine use",
      description: "Our Website also provides the Medicine Support. Medicine is the science and practice of caring for a patient, managing the diagnosis, prognosis, prevention, treatment, palliation of their injury or disease, and promoting their health",
      action: () => window.open('https://www.apollopharmacy.in/', '_blank'),
      buttonText: "Apollo Pharmacy",
      buttonIcon: ExternalLink,
      color: "purple"
    },
    {
      icon: Stethoscope,
      title: "Regular checkup",
      description: "Regular health checks can identify any early signs of health issues.",
      action: () => navigate('/login'),
      buttonText: "Start Checkup",
      buttonIcon: Activity,
      color: "cyan"
    },
    {
      icon: Activity,
      title: "Exercise & Meditation",
      description: "Meditation and Exercise can boost your physical performance, help you achieve your fitness goals, reduce illnesses, increase mind/body awareness, and encourage healthy aging.",
      action: () => window.open('https://youtube.com/playlist?list=PLe1px9-uNQToJhrFIBpVsviZMABuLE5x8&si=mNuM2t7m6L3IpHfG', '_blank'),
      buttonText: "Watch Videos",
      buttonIcon: Youtube,
      color: "indigo"
    }
  ];

  const features = [
    {
      icon: Brain,
      title: "AI-Powered Analysis",
      description: "Advanced machine learning algorithms analyze your responses to provide accurate stress level assessment."
    },
    {
      icon: Stethoscope,
      title: "CBT-Based Questions",
      description: "18 scientifically validated questions based on Cognitive Behavioral Therapy principles."
    },
    {
      icon: Users,
      title: "Professional Doctors",
      description: "Connect with verified mental health professionals for personalized consultation and support."
    },
    {
      icon: Shield,
      title: "Secure & Private",
      description: "Your data is encrypted and protected. We prioritize your privacy and confidentiality."
    },
    {
      icon: TrendingUp,
      title: "Track Progress",
      description: "Monitor your stress levels over time with detailed history and analytics."
    },
    {
      icon: Activity,
      title: "Instant Results",
      description: "Get immediate feedback with personalized recommendations based on your stress level."
    }
  ];

  const getColorClasses = (color: string) => {
    const colors = {
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        icon: 'text-blue-600',
        button: 'bg-blue-600 hover:bg-blue-700'
      },
      green: {
        bg: 'bg-green-50',
        border: 'border-green-200',
        icon: 'text-green-600',
        button: 'bg-green-600 hover:bg-green-700'
      },
      red: {
        bg: 'bg-red-50',
        border: 'border-red-200',
        icon: 'text-red-600',
        button: 'bg-red-600 hover:bg-red-700'
      },
      purple: {
        bg: 'bg-purple-50',
        border: 'border-purple-200',
        icon: 'text-purple-600',
        button: 'bg-purple-600 hover:bg-purple-700'
      },
      cyan: {
        bg: 'bg-cyan-50',
        border: 'border-cyan-200',
        icon: 'text-cyan-600',
        button: 'bg-cyan-600 hover:bg-cyan-700'
      },
      indigo: {
        bg: 'bg-indigo-50',
        border: 'border-indigo-200',
        icon: 'text-indigo-600',
        button: 'bg-indigo-600 hover:bg-indigo-700'
      }
    };
    return colors[color as keyof typeof colors] || colors.blue;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Navigation */}
      <nav className="bg-white/80 backdrop-blur-md shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              
                <img
                  src={stressLogo}
                  alt="AI Stress Detector Logo"
                  className="w-12 h-12 object-contain"
                />
              
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  AI Stress Detector
                </h1>
                <p className="text-xs text-gray-600">Mental Health Support Platform</p>
              </div>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={() => navigate('/login')}
                className="px-6 py-2.5 text-blue-600 hover:text-blue-700 font-semibold transition-colors"
              >
                Login
              </button>
              <button
                onClick={() => navigate('/register')}
                className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl font-semibold"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-16">
          
          <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Understand Your Stress,
            </span>
            <br />
            <span className="text-gray-800">Take Control of Your Life</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-10">
            Advanced AI technology combined with CBT principles to help you identify, 
            understand, and manage your stress levels effectively.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <button
              onClick={() => navigate('/register')}
              className="group px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all shadow-xl hover:shadow-2xl font-semibold text-lg flex items-center justify-center space-x-2"
            >
              <span>Start Free Assessment</span>
              <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
            <button
              onClick={() => navigate('/login')}
              className="px-8 py-4 bg-white text-gray-700 rounded-xl hover:bg-gray-50 transition-all shadow-lg hover:shadow-xl font-semibold text-lg border border-gray-200"
            >
              Sign In
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto mb-20">
          {[
            { value: '95%', label: 'Accuracy Rate' },
            { value: '10k+', label: 'Users Helped' },
            { value: '500+', label: 'Verified Doctors' },
            { value: '24/7', label: 'Support Available' }
          ].map((stat, index) => (
            <div key={index} className="bg-white rounded-2xl p-6 text-center shadow-lg hover:shadow-xl transition-all">
              <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                {stat.value}
              </div>
              <div className="text-sm text-gray-600">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Services Section */}
      <section className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Our Healthcare Services
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Comprehensive healthcare support at your fingertips
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((service, index) => {
              const IconComponent = service.icon;
              const ButtonIcon = service.buttonIcon;
              const colors = getColorClasses(service.color);
              
              return (
                <div
                  key={index}
                  className={`${colors.bg} border ${colors.border} rounded-2xl p-6 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2`}
                >
                  <div className={`inline-flex p-4 ${colors.bg} rounded-xl mb-4`}>
                    <IconComponent className={`w-8 h-8 ${colors.icon}`} />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-gray-800">
                    {service.title}
                  </h3>
                  <p className="text-gray-600 mb-6 text-sm leading-relaxed">
                    {service.description}
                  </p>
                  <button
                    onClick={service.action}
                    className={`w-full ${colors.button} text-white py-3 rounded-xl transition-all font-medium flex items-center justify-center space-x-2 shadow-md hover:shadow-lg`}
                  >
                    <ButtonIcon className="w-5 h-5" />
                    <span>{service.buttonText}</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Why Choose Our Platform?
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Cutting-edge technology meets compassionate care
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const IconComponent = feature.icon;
              return (
                <div
                  key={index}
                  className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border border-gray-100 hover:border-blue-200"
                >
                  <div className="bg-gradient-to-br from-blue-100 to-purple-100 w-16 h-16 rounded-xl flex items-center justify-center mb-6">
                    <IconComponent className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-gray-800">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                How It Works
              </span>
            </h2>
            <p className="text-xl text-gray-600">Simple steps to better mental health</p>
          </div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: '01', title: 'Sign Up', description: 'Create your free account in seconds' },
              { step: '02', title: 'Take Assessment', description: 'Answer 18 CBT-based questions' },
              { step: '03', title: 'Get Results', description: 'Receive AI-powered analysis instantly' },
              { step: '04', title: 'Connect with Doctors', description: 'Book appointments with verified professionals' }
            ].map((item, index) => (
              <div key={index} className="relative text-center">
                <div className="bg-gradient-to-br from-blue-600 to-purple-600 w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-xl mx-auto mb-6 shadow-lg">
                  {item.step}
                </div>
                <h3 className="text-xl font-bold mb-3 text-gray-800">{item.title}</h3>
                <p className="text-gray-600">{item.description}</p>
                {index < 3 && (
                  <div className="hidden md:block absolute top-8 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-blue-300 to-purple-300"></div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Take Control of Your Mental Health?
          </h2>
          <p className="text-xl text-blue-100 mb-10">
            Join thousands of users who have improved their well-being with our AI-powered platform
          </p>
          <button
            onClick={() => navigate('/register')}
            className="px-10 py-4 bg-white text-blue-600 rounded-xl hover:bg-gray-50 transition-all shadow-2xl hover:shadow-3xl font-bold text-lg"
          >
            Start Your Free Assessment Now
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <img
                  src={stressLogo}
                  alt="AI Stress Analyzer Logo"
                  className="w-6 h-6 object-contain"
                />
                <span className="font-bold text-lg">AI Stress Analyzer</span>
              </div>
              <p className="text-gray-400 text-sm">
                Advanced AI-powered mental health assessment platform
              </p>
            </div>
            <div>
              <h4 className="font-bold mb-4">Quick Links</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">About Us</a></li>
                <li><a href="#" className="hover:text-white transition-colors">How It Works</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Our Doctors</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Support</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact Us</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Emergency</h4>
              <div className="space-y-2 text-sm text-gray-400">
                <p>Ambulance: <a href="tel:101" className="text-red-400 hover:text-red-300">101</a></p>
                <p>Crisis Helpline: <a href="tel:9152987821" className="text-blue-400 hover:text-blue-300">9152987821</a></p>
              </div>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8">
            <div className="flex flex-col md:flex-row items-center justify-between">
              <p className="text-center text-sm text-gray-400 mb-4 md:mb-0">
                &copy; 2026 AI Stress Level Analyzer. All rights reserved.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-gray-700 to-gray-800 hover:from-gray-600 hover:to-gray-700 text-gray-300 hover:text-white rounded-lg transition-all duration-300 border border-gray-700 hover:border-gray-600 shadow-md hover:shadow-lg"
              >
                <Shield className="w-4 h-4" />
                <span className="text-sm font-semibold">Admin Login</span>
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;