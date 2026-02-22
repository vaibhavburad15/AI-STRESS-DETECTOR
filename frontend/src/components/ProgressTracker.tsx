// frontend/src/components/ProgressTracker.tsx

import React from 'react';

interface ProgressTrackerProps {
  achievements: any;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ achievements }) => {
  const progressPercentage = Math.min(
    (achievements.points / (achievements.points + achievements.points_to_next_level)) * 100,
    100
  );

  return (
    <div className="progress-tracker">
      {/* Streak */}
      <div className="streak-badge">
        <span className="streak-icon">🔥</span>
        <div>
          <strong>{achievements.streak_days}</strong>
          <span>Day Streak</span>
        </div>
      </div>

      {/* Level Progress */}
      <div className="level-section">
        <div className="level-info">
          <span className="level">Level {achievements.level}</span>
          <span className="level-name">{achievements.level_name}</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <div className="points-info">
          <span>{achievements.points} points</span>
          <span>{achievements.points_to_next_level} to next level</span>
        </div>
      </div>

      {/* Badges */}
      <div className="badges-section">
        <h4>Badges Earned ({achievements.badges.length})</h4>
        <div className="badges-grid">
          {achievements.badges.map((badge: string, i: number) => (
            <div key={i} className="badge">
              {badge}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat">
          <span className="stat-value">{achievements.total_completed}</span>
          <span className="stat-label">Completed</span>
        </div>
        <div className="stat">
          <span className="stat-value">{achievements.meditation_minutes}</span>
          <span className="stat-label">Meditation (mins)</span>
        </div>
        <div className="stat">
          <span className="stat-value">{achievements.exercise_minutes}</span>
          <span className="stat-label">Exercise (mins)</span>
        </div>
        <div className="stat">
          <span className="stat-value">{achievements.journal_entries}</span>
          <span className="stat-label">Journal Entries</span>
        </div>
      </div>
    </div>
  );
};