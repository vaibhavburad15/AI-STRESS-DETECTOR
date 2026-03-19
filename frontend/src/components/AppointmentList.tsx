import React, { useState, useEffect } from 'react';
import api, { appointmentService } from '../services/api';
import { Calendar, Clock, FileText, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';

interface AppointmentListProps {
  userId: string;
}

export const AppointmentList: React.FC<AppointmentListProps> = ({ userId }) => {
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'completed' | 'rejected'>('all');
  const [sharingAppointmentId, setSharingAppointmentId] = useState<string | null>(null);

  useEffect(() => {
    loadAppointments();
  }, [userId]);

  const loadAppointments = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/api/user/appointments/${userId}`);
      setAppointments(data);
    } catch (err) {
      console.error('Failed to load appointments:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status: string) => {
    const configs = {
      pending: {
        color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
        icon: <Clock className="w-5 h-5" />,
        label: 'Pending Review'
      },
      approved: {
        color: 'bg-blue-100 text-blue-800 border-blue-300',
        icon: <CheckCircle className="w-5 h-5" />,
        label: 'Approved'
      },
      completed: {
        color: 'bg-green-100 text-green-800 border-green-300',
        icon: <CheckCircle className="w-5 h-5" />,
        label: 'Completed'
      },
      rejected: {
        color: 'bg-red-100 text-red-800 border-red-300',
        icon: <XCircle className="w-5 h-5" />,
        label: 'Rejected'
      }
    };
    return configs[status as keyof typeof configs] || configs.pending;
  };

  const formatAppointmentLabel = (appointment: any) => {
    if (appointment.slot_label) return appointment.slot_label;
    if (appointment.slot_start_at && appointment.slot_end_at) {
      const start = new Date(appointment.slot_start_at);
      const end = new Date(appointment.slot_end_at);
      return `${start.toLocaleString()} - ${end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    return appointment.time_slot;
  };

  const formatAccessDeadline = (appointment: any) => {
    if (appointment.access_deadline_label) return appointment.access_deadline_label;
    return appointment.access_expires_at ? new Date(appointment.access_expires_at).toLocaleString() : 'Unknown';
  };

  const handleToggleSharing = async (appointmentId: string, shareWithDoctor: boolean) => {
    try {
      setSharingAppointmentId(appointmentId);
      const response = await appointmentService.updateDoctorSharing(appointmentId, shareWithDoctor);
      alert(response.message || 'Sharing preference updated.');
      await loadAppointments();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update sharing preference.');
    } finally {
      setSharingAppointmentId(null);
    }
  };

  const filteredAppointments = appointments.filter(apt => 
    filter === 'all' ? true : apt.status === filter
  );

  const getStatusCounts = () => {
    return {
      all: appointments.length,
      pending: appointments.filter(a => a.status === 'pending').length,
      approved: appointments.filter(a => a.status === 'approved').length,
      completed: appointments.filter(a => a.status === 'completed').length,
      rejected: appointments.filter(a => a.status === 'rejected').length,
    };
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading appointments...</span>
      </div>
    );
  }

  const counts = getStatusCounts();

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
          <h2 className="text-3xl font-bold flex items-center gap-3">
            <Calendar className="w-8 h-8" />
            My Appointments
          </h2>
          <p className="mt-2 text-blue-100">
            Track and manage your scheduled consultations
          </p>
        </div>

        {/* Filters */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex flex-wrap gap-2">
            {[
              { key: 'all', label: 'All', count: counts.all },
              { key: 'pending', label: 'Pending', count: counts.pending },
              { key: 'approved', label: 'Approved', count: counts.approved },
              { key: 'completed', label: 'Completed', count: counts.completed },
              { key: 'rejected', label: 'Rejected', count: counts.rejected },
            ].map(({ key, label, count }) => (
              <button
                key={key}
                onClick={() => setFilter(key as any)}
                className={`
                  px-4 py-2 rounded-lg font-medium transition-all
                  ${filter === key
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {label} ({count})
              </button>
            ))}
          </div>
        </div>

        {/* Appointments List */}
        <div className="p-6">
          {filteredAppointments.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                No {filter !== 'all' ? filter : ''} appointments
              </h3>
              <p className="text-gray-600">
                {filter === 'all' 
                  ? "You haven't booked any appointments yet"
                  : `You don't have any ${filter} appointments`
                }
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAppointments.map((appointment) => {
                const statusConfig = getStatusConfig(appointment.status);
                
                return (
                  <div
                    key={appointment.id}
                    className="border-2 border-gray-200 rounded-xl p-5 hover:shadow-lg transition-all"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      {/* Left: Details */}
                      <div className="flex-1 space-y-3">
                        {/* Doctor */}
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                            {appointment.doctor_name.charAt(0)}
                          </div>
                          <div>
                            <h4 className="font-bold text-gray-900 text-lg">
                              Dr. {appointment.doctor_name}
                            </h4>
                            <p className="text-sm text-gray-600 flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              {formatAppointmentLabel(appointment)}
                            </p>
                          </div>
                        </div>

                        {/* Notes */}
                        {appointment.notes && (
                          <div className="flex items-start gap-2 bg-gray-50 p-3 rounded-lg">
                            <FileText className="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" />
                            <div>
                              <p className="text-xs font-medium text-gray-600 mb-1">Your Notes:</p>
                              <p className="text-sm text-gray-900">{appointment.notes}</p>
                            </div>
                          </div>
                        )}

                        {/* Booked Date */}
                        <p className="text-xs text-gray-500">
                          Booked on {new Date(appointment.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </p>
                        {appointment.data_access_message && (
                          <p className={`text-sm ${appointment.data_access_active ? 'text-green-700' : 'text-gray-500'}`}>
                            {appointment.data_access_message}
                          </p>
                        )}
                        {(appointment.status === 'approved' || appointment.status === 'completed') &&
                          appointment.access_expires_at && (
                            <p className="text-xs text-gray-500">
                              Sharing window closes: {formatAccessDeadline(appointment)}
                            </p>
                          )}
                      </div>

                      {/* Right: Status */}
                      <div className="flex flex-col items-end gap-2">
                        <div className={`
                          px-4 py-2 rounded-lg border-2 font-semibold
                          flex items-center gap-2 ${statusConfig.color}
                        `}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </div>

                        {/* Actions based on status */}
                        {appointment.can_manage_record_sharing && (
                          <button
                            type="button"
                            onClick={() => handleToggleSharing(appointment.id, !appointment.records_shared_with_doctor)}
                            disabled={sharingAppointmentId === appointment.id}
                            className={`text-sm px-3 py-2 rounded-lg text-white ${
                              appointment.records_shared_with_doctor
                                ? 'bg-slate-600 hover:bg-slate-700'
                                : 'bg-blue-600 hover:bg-blue-700'
                            } disabled:opacity-50`}
                          >
                            {sharingAppointmentId === appointment.id
                              ? 'Updating...'
                              : appointment.records_shared_with_doctor
                              ? 'Stop Sharing'
                              : 'Share Details'}
                          </button>
                        )}

                        {appointment.status === 'pending' && (
                          <p className="text-xs text-gray-600 text-right">
                            Waiting for doctor's approval
                          </p>
                        )}

                        {appointment.status === 'completed' && (
                          <p className="text-xs text-green-600 text-right font-medium">
                            ✓ Session completed
                          </p>
                        )}

                        {appointment.status === 'rejected' && (
                          <p className="text-xs text-red-600 text-right">
                            Please book another slot
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Stats Footer */}
        {appointments.length > 0 && (
          <div className="bg-gray-50 p-6 border-t border-gray-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-blue-600">{counts.all}</p>
                <p className="text-sm text-gray-600">Total Appointments</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-600">{counts.pending}</p>
                <p className="text-sm text-gray-600">Pending</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-600">{counts.approved}</p>
                <p className="text-sm text-gray-600">Approved</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{counts.completed}</p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
