import React, { useState } from 'react';
import { Star } from 'lucide-react';

interface RecommendationCardProps {
  recommendation: any;
  onStart: (id: string) => void;
  onComplete: (id: string, rating?: number, notes?: string) => void;
}

const getRecommendationSourceLabel = (recommendation: any): string => {
  if (recommendation?.source === 'llm') {
    return 'AI-personalized';
  }
  return 'Rule-based fallback';
};

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onStart,
  onComplete
}) => {
  const [showRating, setShowRating] = useState(false);
  const [rating, setRating] = useState(0);
  const [notes, setNotes] = useState('');

  const submitCompletion = () => {
    onComplete(recommendation.id, rating, notes);
    setShowRating(false);
    setRating(0);
    setNotes('');
  };

  return (
    <div className={`recommendation-card priority-${recommendation.priority}`}>
      <div className="card-icon">{recommendation.icon}</div>

      <div className="card-content">
        <div className="card-badges">
          <span className={`recommendation-source source-${recommendation.source || 'rule_based'}`}>
            {getRecommendationSourceLabel(recommendation)}
          </span>
        </div>

        <h3 className="card-title">{recommendation.title}</h3>
        <p className="card-description">{recommendation.description}</p>

        <div className="card-meta">
          <span className="duration">Time: {recommendation.duration}</span>
          <span className={`difficulty ${recommendation.difficulty}`}>
            {recommendation.difficulty}
          </span>
          <span className="effectiveness">
            {recommendation.effectiveness}% effective
          </span>
        </div>

        {recommendation.instructions && (
          <div className="instructions">
            <h4>How to do it:</h4>
            <ol>
              {recommendation.instructions.map((inst: string, i: number) => (
                <li key={i}>{inst}</li>
              ))}
            </ol>
          </div>
        )}

        <div className="card-actions">
          <button
            onClick={() => onStart(recommendation.id)}
            className="btn-primary"
          >
            {recommendation.action} {'->'}
          </button>
          <button
            onClick={() => setShowRating(true)}
            className="btn-secondary"
          >
            Mark Done
          </button>
        </div>

        {showRating && (
          <div className="rating-modal">
            <h4>How effective was this?</h4>
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  className={`star ${rating >= star ? 'filled' : ''}`}
                  onClick={() => setRating(star)}
                />
              ))}
            </div>
            <textarea
              placeholder="Add notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
            <div className="modal-actions">
              <button onClick={submitCompletion} className="btn-primary">
                Submit
              </button>
              <button onClick={() => setShowRating(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
