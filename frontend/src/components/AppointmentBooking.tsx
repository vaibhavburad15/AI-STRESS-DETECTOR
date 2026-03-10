import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Calendar, Clock, User, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface AppointmentBookingProps {
  userId: string;
}

export const AppointmentBooking: React.FC<AppointmentBookingProps> = ({ userId }) => {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedDoctor, setSelectedDoctor] = useState<any>(null);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDoctors();
  }, []);

  const loadDoctors = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/api/user/doctors');
      setDoctors(data);
    } catch (err: any) {
      setError('Failed to load doctors');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBookAppointment = async () => {
    if (!selectedDoctor || !selectedSlot) {
      setError('Please select a doctor and time slot');
      return;
    }

    try {
      setBooking(true);
      setError('');
      
      await api.post('/api/user/appointment/book', {
        user_id: userId,
        doctor_id: selectedDoctor.id,
        time_slot: selectedSlot,
        notes,
      });

      setSuccess(true);
      
      // Reset form after 2 seconds
      setTimeout(() => {
        setSuccess(false);
        setSelectedDoctor(null);
        setSelectedSlot('');
        setNotes('');
      }, 2000);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to book appointment');
    } finally {
      setBooking(false);
    }
  };

  const formatSlot = (slot: string) => {
    // ✅ MEDIUM FIX: Handle both ISO format and informal format
    // Try to parse as ISO first
    const isoDate = new Date(slot);
    
    // If it's a valid ISO date
    if (!isNaN(isoDate.getTime())) {
      return isoDate.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    }
    
    // If it's already in informal format (e.g., "Mon 9:00-10:00"), return as-is
    return slot;
  };

  const groupSlotsByDate = (slots: string[]) => {
    const grouped: { [key: string]: string[] } = {};
    
    slots.forEach(slot => {
      // Try to parse as ISO, fall back to informal format
      const isoDate = new Date(slot);
      let dateKey: string;
      
      if (!isNaN(isoDate.getTime())) {
        dateKey = isoDate.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        });
      } else {
        // For informal slots like "Mon 9:00-10:00", group by day
        const dayPart = slot.split(' ')[0];
        dateKey = `${dayPart} (recurring)`;
      }
      
      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(slot);
    });
    
    return grouped;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading doctors...</span>
      </div>
    );
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-8 p-8 bg-green-50 border-2 border-green-200 rounded-2xl text-center">
        <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
        <h3 className="text-2xl font-bold text-green-900 mb-2">Appointment Booked!</h3>
        <p className="text-green-700">
          Your appointment with Dr. {selectedDoctor?.name} has been scheduled.
        </p>
        <p className="text-sm text-green-600 mt-2">
          You'll receive a confirmation email shortly.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
          <h2 className="text-3xl font-bold flex items-center gap-3">
            <Calendar className="w-8 h-8" />
            Book an Appointment
          </h2>
          <p className="mt-2 text-blue-100">
            Schedule a consultation with one of our verified mental health professionals
          </p>
        </div>

        <div className="p-6">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {/* Step 1: Select Doctor */}
          <div className="mb-8">
            <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <User className="w-6 h-6 text-blue-600" />
              Step 1: Choose Your Doctor
            </h3>
            
            {doctors.length === 0 ? (
              <div className="text-center p-8 bg-gray-50 rounded-xl">
                <p className="text-gray-600">No doctors available at the moment</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-4">
                {doctors.map((doctor) => (
                  <div
                    key={doctor.id}
                    onClick={() => setSelectedDoctor(doctor)}
                    className={`
                      p-5 border-2 rounded-xl cursor-pointer transition-all
                      ${selectedDoctor?.id === doctor.id
                        ? 'border-blue-600 bg-blue-50 shadow-lg'
                        : 'border-gray-200 hover:border-blue-300 hover:shadow-md'
                      }
                    `}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                        {doctor.name.charAt(0)}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-gray-900">Dr. {doctor.name}</h4>
                        <p className="text-sm text-gray-600">{doctor.specialization}</p>
                        <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                          <Clock className="w-4 h-4" />
                          {doctor.available_slots.length} slots available
                        </div>
                      </div>
                      {selectedDoctor?.id === doctor.id && (
                        <CheckCircle className="w-6 h-6 text-blue-600" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Step 2: Select Time Slot */}
          {selectedDoctor && (
            <div className="mb-8 animate-fadeIn">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Clock className="w-6 h-6 text-blue-600" />
                Step 2: Choose Time Slot
              </h3>
              
              {selectedDoctor.available_slots.length === 0 ? (
                <div className="text-center p-8 bg-gray-50 rounded-xl">
                  <p className="text-gray-600">No available slots for this doctor</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(groupSlotsByDate(selectedDoctor.available_slots)).map(([date, slots]) => (
                    <div key={date} className="bg-gray-50 rounded-xl p-4">
                      <h4 className="font-semibold text-gray-900 mb-3">{date}</h4>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                        {(slots as string[]).map((slot) => (
                          <button
                            key={slot}
                            onClick={() => setSelectedSlot(slot)}
                            className={`
                              px-4 py-2 rounded-lg font-medium transition-all
                              ${selectedSlot === slot
                                ? 'bg-blue-600 text-white shadow-lg'
                                : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-400 hover:bg-blue-50'
                              }
                            `}
                          >
                            {new Date(slot).toLocaleTimeString('en-US', {
                              hour: 'numeric',
                              minute: '2-digit',
                              hour12: true
                            })}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Add Notes */}
          {selectedSlot && (
            <div className="mb-8 animate-fadeIn">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="w-6 h-6 text-blue-600" />
                Step 3: Add Notes (Optional)
              </h3>
              
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Describe your concerns or what you'd like to discuss..."
                rows={4}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-blue-500 focus:outline-none resize-none"
              />
              <p className="mt-2 text-sm text-gray-500">
                This helps the doctor prepare for your session
              </p>
            </div>
          )}

          {/* Summary & Book Button */}
          {selectedSlot && (
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 animate-fadeIn">
              <h4 className="font-bold text-gray-900 mb-4">Appointment Summary</h4>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3">
                  <User className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="text-sm text-gray-600">Doctor</p>
                    <p className="font-semibold text-gray-900">Dr. {selectedDoctor.name}</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="text-sm text-gray-600">Date & Time</p>
                    <p className="font-semibold text-gray-900">{formatSlot(selectedSlot)}</p>
                  </div>
                </div>

                {notes && (
                  <div className="flex items-start gap-3">
                    <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-gray-600">Notes</p>
                      <p className="text-gray-900">{notes}</p>
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleBookAppointment}
                disabled={booking}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-bold text-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {booking ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" />
                    Booking...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-6 h-6" />
                    Confirm Appointment
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};