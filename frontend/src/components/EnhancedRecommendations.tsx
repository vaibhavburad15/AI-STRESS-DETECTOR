// frontend/src/components/EnhancedRecommendations.tsx

import React, { useState, useEffect } from 'react';
import { RecommendationCard } from './RecommendationCard';
import { ProgressTracker } from './ProgressTracker';
import api from '../services/api';

interface EnhancedRecommendationsProps {
  testId: string;
  userId: string;
}

export const EnhancedRecommendations: React.FC<EnhancedRecommendationsProps> = ({ testId, userId }) => {
  const [recommendations, setRecommendations] = useState<any>(null);
  const [achievements, setAchievements] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('immediate');

  useEffect(() => {
    loadRecommendations();
    loadAchievements();
  }, [testId]);

  const loadRecommendations = async () => {
    try {
      const { data } = await api.post(`/api/user/recommendations/enhanced`, { test_id: testId });
      setRecommendations(data);
    } catch (error) {
      console.error('Failed to load recommendations', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAchievements = async () => {
    try {
      const { data } = await api.get(`/api/user/achievements/${userId}`);
      setAchievements(data);
    } catch (error) {
      console.error('Failed to load achievements', error);
    }
  };

  const handleStart = async (recommendationId: string) => {
    try {
      await api.post('/api/user/recommendations/start', {
        user_id: userId,
        recommendation_id: recommendationId
      });
      alert('Recommendation started! +5 points');
      loadAchievements();
    } catch (error) {
      console.error('Failed to start recommendation', error);
    }
  };

  const handleComplete = async (recommendationId: string, rating?: number, notes?: string) => {
    try {
      const { data } = await api.post('/api/user/recommendations/complete', {
        user_id: userId,
        recommendation_id: recommendationId,
        effectiveness_rating: rating,
        notes: notes
      });
      
      alert(`Completed! +${data.points_earned} points!`);
      if (data.new_badges.length > 0) {
        alert(`New badge earned: ${data.new_badges.join(', ')}`);
      }
      
      loadAchievements();
    } catch (error) {
      console.error('Failed to complete recommendation', error);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-8"><div className="animate-spin">Loading...</div></div>;
  }

  if (!recommendations) {
    return <div>No recommendations available</div>;
  }

  const categories = [
    { key: 'immediate', label: '⚡ Right Now', icon: '⚡' },
    { key: 'daily', label: '📅 Daily Habits', icon: '📅' },
    { key: 'weekly', label: '🗓️ Weekly Goals', icon: '🗓️' },
    { key: 'lifestyle', label: '🌱 Lifestyle', icon: '🌱' },
    { key: 'professional', label: '👨‍⚕️ Professional', icon: '👨‍⚕️' }
  ];

  return (
    <div className="enhanced-recommendations-container">
      {/* Progress Tracker */}
      {achievements && (
        <ProgressTracker achievements={achievements} />
      )}

      {/* Summary Banner */}
      <div className={`summary-banner priority-${recommendations.summary.priority}`}>
        <h2 className="text-2xl font-bold">{recommendations.summary.title}</h2>
        <div className="stress-indicator">
          <span className="stress-label">{recommendations.summary.stress_label}</span>
          {recommendations.summary.action_required && (
            <span className="urgent-tag">⚠️ Action Required</span>
          )}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="category-tabs">
        {categories.map(cat => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`tab ${activeCategory === cat.key ? 'active' : ''}`}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
            <span className="count">{recommendations[cat.key]?.length || 0}</span>
          </button>
        ))}
      </div>

      {/* Recommendations Grid */}
      <div className="recommendations-grid">
        {recommendations[activeCategory]?.map((rec: any) => (
          <RecommendationCard
            key={rec.id}
            recommendation={rec}
            onStart={handleStart}
            onComplete={handleComplete}
          />
        ))}
      </div>

      {/* Quick Wins Section */}
      {recommendations.quick_wins && recommendations.quick_wins.length > 0 && (
        <div className="quick-wins">
          <h3>⚡ Quick Wins (30-60 seconds)</h3>
          <div className="quick-wins-list">
            {recommendations.quick_wins.map((qw: any) => (
              <div key={qw.id} className="quick-win-card">
                <span className="icon">{qw.icon}</span>
                <div>
                  <strong>{qw.title}</strong>
                  <p>{qw.description}</p>
                  <span className="duration">{qw.duration}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};