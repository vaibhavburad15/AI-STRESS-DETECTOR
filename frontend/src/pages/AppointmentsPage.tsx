import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { AppointmentBooking } from '../components/AppointmentBooking';
import { AppointmentList } from '../components/AppointmentList';
import { Calendar, List, ArrowLeft } from 'lucide-react';

const AppointmentsPage = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [activeTab, setActiveTab] = useState<'book' | 'list'>('list');

  if (!user) {
    navigate('/login');
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/user/dashboard')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-6 h-6 text-gray-600" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
                <p className="text-sm text-gray-600">Manage your consultations</p>
              </div>
            </div>
            
            <button
              onClick={() => {
                authService.logout();
                navigate('/login');
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b sticky top-[73px] z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('list')}
              className={`
                flex items-center gap-2 px-6 py-4 font-semibold transition-all
                ${activeTab === 'list'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
                }
              `}
            >
              <List className="w-5 h-5" />
              My Appointments
            </button>
            
            <button
              onClick={() => setActiveTab('book')}
              className={`
                flex items-center gap-2 px-6 py-4 font-semibold transition-all
                ${activeTab === 'book'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
                }
              `}
            >
              <Calendar className="w-5 h-5" />
              Book New Appointment
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="py-8">
        {activeTab === 'list' && (
          <AppointmentList userId={user.id} />
        )}
        
        {activeTab === 'book' && (
          <AppointmentBooking userId={user.id} />
        )}
      </div>
    </div>
  );
};

export default AppointmentsPage;