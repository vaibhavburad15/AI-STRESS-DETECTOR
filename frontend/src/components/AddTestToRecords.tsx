/**
 * Add Test to Medical Records Component
 * File: frontend/src/components/AddTestToRecords.tsx
 * 
 * Use this component on the test results page to allow users to add their stress test
 * results to their medical records.
 */

import React, { useState } from 'react';
import { FileText, Plus, Check, X } from 'lucide-react';
import axios from 'axios';

interface Props {
  userId: string;
  testId: string;
  stressLevel: number;
  stressLabel: string;
  confidenceScore: number;
  testDate: string;
  onSuccess?: () => void;
}

const AddTestToRecords: React.FC<Props> = ({
  userId,
  testId,
  stressLevel,
  stressLabel,
  confidenceScore,
  testDate,
  onSuccess
}) => {
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState(false);
  const [recordName, setRecordName] = useState(
    `Stress Test - ${new Date(testDate).toLocaleDateString()}`
  );
  const [notes, setNotes] = useState('');

  const handleAddToRecords = async () => {
    try {
      setLoading(true);
      await axios.post(
        '/api/medical-records/link-stress-test',
        {
          user_id: userId,
          stress_test_id: testId,
          add_to_medical_records: true,
          record_name: recordName,
          notes: notes
        },
        {
          headers: {
            'X-User-ID': userId
          }
        }
      );
      
      setAdded(true);
      setShowModal(false);
      
      if (onSuccess) {
        onSuccess();
      }
      
      // Show success notification
      alert('Stress test added to medical records!');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to add test to medical records');
    } finally {
      setLoading(false);
    }
  };

  if (added) {
    return (
      <div className="flex items-center gap-2 text-green-600 bg-green-50 px-4 py-2 rounded-lg">
        <Check className="w-5 h-5" />
        <span className="text-sm font-medium">Added to Medical Records</span>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        <Plus className="w-5 h-5" />
        Add to Medical Records
      </button>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">Add Test to Medical Records</h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Test Summary */}
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-3 mb-3">
                <FileText className="w-8 h-8 text-blue-600" />
                <div>
                  <div className="font-semibold">Stress Assessment</div>
                  <div className="text-sm text-gray-600">
                    {new Date(testDate).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Stress Level:</span>
                  <span className={`font-semibold ${
                    stressLevel === 0 ? 'text-green-600' :
                    stressLevel === 1 ? 'text-yellow-600' :
                    stressLevel === 2 ? 'text-orange-600' :
                    'text-red-600'
                  }`}>
                    {stressLabel}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Confidence:</span>
                  <span className="font-semibold">{(confidenceScore * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Record Name</label>
                <input
                  type="text"
                  value={recordName}
                  onChange={(e) => setRecordName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Stress Test - Jan 2024"
                />
                <p className="text-xs text-gray-500 mt-1">
                  This name will appear in your medical records
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Notes (Optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Add any notes about this test or recommendations..."
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleAddToRecords}
                disabled={loading || !recordName}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {loading ? 'Adding...' : 'Add to Records'}
              </button>
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>

            {/* Info */}
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-xs text-blue-800">
                💡 This will create a record in your medical files with your test results and recommendations. 
                You can view and download it anytime from the Medical Records section.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AddTestToRecords;