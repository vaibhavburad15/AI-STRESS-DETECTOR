import React, { useEffect, useState } from 'react';
import { RecommendationCard } from './RecommendationCard';
import api from '../services/api';

interface EnhancedRecommendationsProps {
  testId: string;
  userId: string;
}

const getSummarySourceLabel = (recommendations: any): string => {
  const primarySource = recommendations?.meta?.primary_source || recommendations?.summary?.source;
  if (primarySource === 'llm') {
    return 'AI-powered recommendations';
  }
  return 'Rule-based recommendations';
};

export const EnhancedRecommendations: React.FC<EnhancedRecommendationsProps> = ({ testId, userId }) => {
  const [recommendations, setRecommendations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('immediate');

  useEffect(() => {
    loadRecommendations();
  }, [testId]);

  const loadRecommendations = async () => {
    try {
      const { data } = await api.post('/api/user/recommendations/enhanced', null, {
        params: { test_id: testId }
      });
      setRecommendations(data);
    } catch (error) {
      console.error('Failed to load recommendations', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (recommendationId: string) => {
    try {
      await api.post('/api/user/recommendations/start', {
        user_id: userId,
        recommendation_id: recommendationId
      });
      alert('Recommendation started!');
    } catch (error) {
      console.error('Failed to start recommendation', error);
    }
  };

  const handleComplete = async (recommendationId: string, rating?: number, notes?: string) => {
    try {
      await api.post('/api/user/recommendations/complete', {
        user_id: userId,
        recommendation_id: recommendationId,
        effectiveness_rating: rating,
        notes
      });
      alert('Recommendation marked as completed.');
    } catch (error) {
      console.error('Failed to complete recommendation', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <div className="text-center">
          <div className="animate-spin">Loading...</div>
          <p className="mt-3 text-sm text-slate-500">
            Personalized recommendations are still being prepared. Your assessment result is already ready.
          </p>
        </div>
      </div>
    );
  }

  if (!recommendations) {
    return <div>No recommendations available</div>;
  }

  const categories = [
    { key: 'immediate', label: 'Right Now', icon: 'Now' },
    { key: 'daily', label: 'Daily Habits', icon: 'Day' },
    { key: 'weekly', label: 'Weekly Goals', icon: 'Week' },
    { key: 'lifestyle', label: 'Lifestyle', icon: 'Life' },
    { key: 'professional', label: 'Professional', icon: 'Care' }
  ];

  return (
    <div className="enhanced-recommendations-container">
      <div className={`summary-banner priority-${recommendations.summary.priority}`}>
        <div className="summary-source-row">
          <span className={`source-pill source-${recommendations.meta?.primary_source || recommendations.summary.source || 'rule_based'}`}>
            {getSummarySourceLabel(recommendations)}
          </span>
        </div>

        <h2 className="text-2xl font-bold">{recommendations.summary.title}</h2>
        {recommendations.summary.body && (
          <p className="summary-body">{recommendations.summary.body}</p>
        )}

        <div className="stress-indicator">
          <span className="stress-label">{recommendations.summary.stress_label}</span>
          {recommendations.summary.action_required && (
            <span className="urgent-tag">Action Required</span>
          )}
        </div>
      </div>

      <div className="category-tabs">
        {categories.map((cat) => (
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
    </div>
  );
};
