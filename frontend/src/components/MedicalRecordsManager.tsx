/**
 * Medical Records Manager Component
 * File: frontend/src/components/MedicalRecordsManager.tsx
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Download, Trash2, Search, 
  FileText, Image, File, X, Calendar,
  ExternalLink
} from 'lucide-react';
import api, { medicalRecordsService } from '../services/api';

// ✅ MEDIUM FIX: Use shared API client instead of raw axios
// This ensures JWT authentication is properly applied to all requests

interface MedicalRecord {
  id: string;
  user_id: string;
  record_name: string;
  record_type: string;
  file_name: string;
  file_size: number;
  file_format: string;
  description?: string;
  record_date?: string;
  doctor_name?: string;
  hospital_name?: string;
  notes?: string;
  tags: string[];
  uploaded_at: string;
  updated_at?: string;
  download_count: number;
  is_linked_to_stress_test: boolean;
  linked_test_id?: string;
}

interface RecordStats {
  total_records: number;
  total_size_mb: number;
  records_by_type: { [key: string]: number };
  recent_uploads: number;
  stress_tests_linked: number;
  most_recent_upload: string | null;
  storage_limit_mb: number;
  storage_used_mb: number;
  storage_percentage: number;
}

interface Props {
  userId: string;
}

const MedicalRecordsManager: React.FC<Props> = ({ userId }) => {
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [stats, setStats] = useState<RecordStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set());
  
  // Upload form state
  const [uploadForm, setUploadForm] = useState({
    file: null as File | null,
    record_name: '',
    record_type: 'other',
    description: '',
    record_date: '',
    doctor_name: '',
    hospital_name: '',
    notes: '',
    tags: ''
  });
  
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const recordTypes = [
    { value: 'prescription', label: '💊 Prescription', icon: '💊' },
    { value: 'lab_report', label: '🧪 Lab Report', icon: '🧪' },
    { value: 'imaging', label: '📸 Imaging', icon: '📸' },
    { value: 'diagnosis', label: '🩺 Diagnosis', icon: '🩺' },
    { value: 'stress_test', label: '📊 Stress Test', icon: '📊' },
    { value: 'therapy_notes', label: '📝 Therapy Notes', icon: '📝' },
    { value: 'insurance', label: '📋 Insurance', icon: '📋' },
    { value: 'other', label: '📄 Other', icon: '📄' }
  ];

  useEffect(() => {
    fetchRecords();
    fetchStats();
  }, [userId, filterType, searchQuery]);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      // ✅ FIX: Use shared medicalRecordsService with JWT auth
      const data = await medicalRecordsService.getRecords(userId, {
        record_type: filterType !== 'all' ? filterType : undefined,
        search: searchQuery || undefined,
      });
      setRecords(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Failed to fetch records:', error);
      setRecords([]);
      alert('Failed to load medical records: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      // ✅ FIX: Use shared medicalRecordsService with JWT auth
      const data = await medicalRecordsService.getStats(userId);
      setStats(data);
    } catch (error: any) {
      console.error('Failed to fetch stats:', error);
      setStats({
        total_records: 0,
        total_size_mb: 0,
        records_by_type: {},
        recent_uploads: 0,
        stress_tests_linked: 0,
        storage_limit_mb: 100,
        storage_used_mb: 0,
        storage_percentage: 0,
        most_recent_upload: null
      });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadForm(prev => ({
        ...prev,
        file,
        record_name: prev.record_name || file.name.split('.')[0]
      }));
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setUploadForm(prev => ({
        ...prev,
        file,
        record_name: prev.record_name || file.name.split('.')[0]
      }));
    }
  };

  const handleUpload = async () => {
    if (!uploadForm.file) {
      alert('Please select a file');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadForm.file);
    formData.append('user_id', userId);
    formData.append('record_name', uploadForm.record_name);
    formData.append('record_type', uploadForm.record_type);
    if (uploadForm.description) formData.append('description', uploadForm.description);
    if (uploadForm.record_date) formData.append('record_date', uploadForm.record_date);
    if (uploadForm.doctor_name) formData.append('doctor_name', uploadForm.doctor_name);
    if (uploadForm.hospital_name) formData.append('hospital_name', uploadForm.hospital_name);
    if (uploadForm.notes) formData.append('notes', uploadForm.notes);
    if (uploadForm.tags) formData.append('tags', uploadForm.tags);

    try {
      setLoading(true);
      // Use shared api client with JWT auth
      const formDataToSend = new FormData();
      formDataToSend.append('file', uploadForm.file);
      formDataToSend.append('record_name', uploadForm.record_name);
      formDataToSend.append('record_type', uploadForm.record_type);
      if (uploadForm.description) formDataToSend.append('description', uploadForm.description);
      if (uploadForm.record_date) formDataToSend.append('record_date', uploadForm.record_date);
      if (uploadForm.doctor_name) formDataToSend.append('doctor_name', uploadForm.doctor_name);
      if (uploadForm.hospital_name) formDataToSend.append('hospital_name', uploadForm.hospital_name);
      if (uploadForm.notes) formDataToSend.append('notes', uploadForm.notes);
      if (uploadForm.tags) formDataToSend.append('tags', uploadForm.tags);
      
      await medicalRecordsService.uploadRecord(formDataToSend);
      
      setShowUploadModal(false);
      setUploadForm({
        file: null,
        record_name: '',
        record_type: 'other',
        description: '',
        record_date: '',
        doctor_name: '',
        hospital_name: '',
        notes: '',
        tags: ''
      });
      setUploadProgress(0);
      fetchRecords();
      fetchStats();
      alert('File uploaded successfully!');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to upload file');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (record: MedicalRecord) => {
    try {
      const isStressTest = record.is_linked_to_stress_test || record.record_type === 'stress_test';

      const blob = await medicalRecordsService.downloadRecord(record.id);

      // Always use PDF for stress test records regardless of stored file_name
      const blobType = isStressTest ? 'application/pdf' : 'application/octet-stream';
      const fileName = isStressTest
        ? `${record.record_name.replace(/\s+/g, '_')}.pdf`
        : record.file_name;

      const url = window.URL.createObjectURL(new Blob([blob], { type: blobType }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      fetchRecords(); // Refresh to update download count
    } catch (error) {
      alert('Failed to download file');
    }
  };

  const handleBulkDownload = async () => {
    if (selectedRecords.size === 0) {
      alert('Please select records to download');
      return;
    }

    try {
      // Use api client directly for bulk download
      const response = await api.post(
        '/api/medical-records/download/bulk',
        { user_id: userId, record_ids: Array.from(selectedRecords) },
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `medical_records_${new Date().toISOString().split('T')[0]}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setSelectedRecords(new Set());
    } catch (error) {
      alert('Failed to download files');
    }
  };

  const handleDelete = async (recordId: string) => {
    if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
      return;
    }

    try {
      await medicalRecordsService.deleteRecord(recordId);
      fetchRecords();
      fetchStats();
      alert('Record deleted successfully');
    } catch (error) {
      alert('Failed to delete record');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getFileIcon = (format: string) => {
    if (['jpg', 'jpeg', 'png'].includes(format)) return <Image className="w-5 h-5" />;
    if (format === 'pdf') return <FileText className="w-5 h-5" />;
    return <File className="w-5 h-5" />;
  };

  const filteredRecords = Array.isArray(records) ? records.filter(record => {
    if (filterType !== 'all' && record.record_type !== filterType) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        record.record_name.toLowerCase().includes(query) ||
        record.description?.toLowerCase().includes(query) ||
        record.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }
    return true;
  }) : [];

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Medical Records</h1>
          <p className="text-gray-600 mt-1">Manage and organize your medical documents</p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Upload className="w-5 h-5" />
          Upload Record
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Total Records</div>
            <div className="text-2xl font-bold text-blue-600">{stats.total_records}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Storage Used</div>
            <div className="text-2xl font-bold text-purple-600">
              {stats.storage_used_mb?.toFixed(1) || '0.0'} MB
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {stats.storage_percentage?.toFixed(1) || '0.0'}% of {stats.storage_limit_mb || 100} MB
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Recent Uploads</div>
            <div className="text-2xl font-bold text-green-600">{stats.recent_uploads || 0}</div>
            <div className="text-xs text-gray-500 mt-1">Last 30 days</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Stress Tests</div>
            <div className="text-2xl font-bold text-orange-600">{stats.stress_tests_linked || 0}</div>
            <div className="text-xs text-gray-500 mt-1">Linked to records</div>
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search records..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            {recordTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          {selectedRecords.size > 0 && (
            <button
              onClick={handleBulkDownload}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Download className="w-5 h-5" />
              Download Selected ({selectedRecords.size})
            </button>
          )}
        </div>
      </div>

      {/* Records Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            Loading records...
          </div>
        ) : filteredRecords.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p>No medical records found</p>
            <button
              onClick={() => setShowUploadModal(true)}
              className="mt-4 text-blue-600 hover:underline"
            >
              Upload your first record
            </button>
          </div>
        ) : (
          filteredRecords.map(record => (
            <div
              key={record.id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedRecords.has(record.id)}
                    onChange={(e) => {
                      const newSelected = new Set(selectedRecords);
                      if (e.target.checked) {
                        newSelected.add(record.id);
                      } else {
                        newSelected.delete(record.id);
                      }
                      setSelectedRecords(newSelected);
                    }}
                    className="rounded"
                  />
                  {getFileIcon(record.file_format)}
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleDownload(record)}
                    className="p-1 hover:bg-gray-100 rounded"
                    title="Download"
                  >
                    <Download className="w-4 h-4 text-gray-600" />
                  </button>
                  <button
                    onClick={() => handleDelete(record.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              </div>

              <h3 className="font-semibold text-gray-900 mb-2">{record.record_name}</h3>
              
              <div className="space-y-1 text-sm text-gray-600 mb-3">
                <div className="flex items-center gap-1">
                  {recordTypes.find(t => t.value === record.record_type)?.icon}
                  <span>{recordTypes.find(t => t.value === record.record_type)?.label.split(' ')[1]}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {formatDate(record.uploaded_at)}
                </div>
                <div>{formatFileSize(record.file_size)} • {record.file_format.toUpperCase()}</div>
                {record.download_count > 0 && (
                  <div className="text-xs text-gray-500">
                    Downloaded {record.download_count} time{record.download_count !== 1 ? 's' : ''}
                  </div>
                )}
              </div>

              {record.description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{record.description}</p>
              )}

              {record.tags && record.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {record.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {record.is_linked_to_stress_test && (
                <div className="mt-3 pt-3 border-t flex items-center gap-2 text-xs text-purple-600">
                  <ExternalLink className="w-4 h-4" />
                  Linked to stress test
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Upload Medical Record</h2>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="p-2 hover:bg-gray-100 rounded"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* File Upload Area */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center mb-6 ${
                  dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  className="hidden"
                />
                {uploadForm.file ? (
                  <div className="flex items-center justify-center gap-3">
                    <FileText className="w-12 h-12 text-blue-600" />
                    <div className="text-left">
                      <div className="font-medium">{uploadForm.file.name}</div>
                      <div className="text-sm text-gray-500">
                        {formatFileSize(uploadForm.file.size)}
                      </div>
                    </div>
                    <button
                      onClick={() => setUploadForm(prev => ({ ...prev, file: null }))}
                      className="p-2 hover:bg-gray-100 rounded"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-2">Drag and drop your file here</p>
                    <p className="text-sm text-gray-500 mb-4">
                      or click to browse (PDF, JPG, PNG, DOC - Max 10MB)
                    </p>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Select File
                    </button>
                  </>
                )}
              </div>

              {/* Upload Progress */}
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="mb-6">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600 mt-2">Uploading... {uploadProgress}%</p>
                </div>
              )}

              {/* Form Fields */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Record Name *</label>
                  <input
                    type="text"
                    value={uploadForm.record_name}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, record_name: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., Blood Test Results - Jan 2024"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Record Type *</label>
                  <select
                    value={uploadForm.record_type}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, record_type: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    {recordTypes.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={uploadForm.description}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    rows={3}
                    placeholder="Brief description of this record..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Record Date</label>
                    <input
                      type="date"
                      value={uploadForm.record_date}
                      onChange={(e) => setUploadForm(prev => ({ ...prev, record_date: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Doctor Name</label>
                    <input
                      type="text"
                      value={uploadForm.doctor_name}
                      onChange={(e) => setUploadForm(prev => ({ ...prev, doctor_name: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="Dr. Smith"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Hospital/Clinic Name</label>
                  <input
                    type="text"
                    value={uploadForm.hospital_name}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, hospital_name: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="City Hospital"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Notes</label>
                  <textarea
                    value={uploadForm.notes}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, notes: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    rows={2}
                    placeholder="Additional notes..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={uploadForm.tags}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, tags: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="urgent, follow-up, chronic"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleUpload}
                  disabled={!uploadForm.file || !uploadForm.record_name || loading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
                >
                  {loading ? 'Uploading...' : 'Upload Record'}
                </button>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MedicalRecordsManager;