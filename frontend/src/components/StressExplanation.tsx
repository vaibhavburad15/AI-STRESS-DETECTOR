import { useEffect, useState } from 'react';
import { AlertTriangle, Brain, Download, Info } from 'lucide-react';
import { explainabilityService } from '../services/api';
import type { StressExplanation as ExplanationType, CategoryScore, RiskFactor, CrisisData } from '../types';

interface Props {
  testId: string;
  testData?: {
    explanation?: ExplanationType;
    category_scores?: Record<string, CategoryScore>;
    risk_factors?: RiskFactor[];
    continuous_score?: number;
    probabilities?: Record<string, number>;
    crisis?: CrisisData;
  };
}

const severityColor = (severity: string) => {
  switch (severity.toLowerCase()) {
    case 'low':
      return 'text-emerald-600 bg-emerald-50';
    case 'moderate':
      return 'text-amber-600 bg-amber-50';
    case 'high':
      return 'text-orange-600 bg-orange-50';
    case 'severe':
    case 'critical':
      return 'text-red-600 bg-red-50';
    default:
      return 'text-slate-600 bg-slate-50';
  }
};

const StressExplanation = ({ testId, testData }: Props) => {
  const [explanation, setExplanation] = useState<ExplanationType | null>(testData?.explanation || null);
  const [categoryScores, setCategoryScores] = useState<Record<string, CategoryScore>>(testData?.category_scores || {});
  const [riskFactors, setRiskFactors] = useState<RiskFactor[]>(testData?.risk_factors || []);
  const [continuousScore, setContinuousScore] = useState<number | undefined>(testData?.continuous_score);
  const [probabilities, setProbabilities] = useState<Record<string, number>>(testData?.probabilities || {});
  const [crisis] = useState<CrisisData | undefined>(testData?.crisis);
  const [loading, setLoading] = useState(!testData?.explanation);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!testData?.explanation) {
      loadExplanation();
    }
  }, [testId]);

  const loadExplanation = async () => {
    try {
      const data = await explainabilityService.getTestExplanation(testId);
      setExplanation(data.explanation);
      setCategoryScores(data.category_scores || {});
      setRiskFactors(data.risk_factors || []);
      setContinuousScore(data.continuous_score);
      setProbabilities(data.probabilities || {});
    } catch (error) {
      console.error('Failed to load explanation', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async () => {
    setDownloading(true);
    try {
      const blob = await explainabilityService.downloadReport(testId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `stress_report_${testId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error('Failed to download report', error);
      alert('Failed to download report');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 text-center text-slate-500">
        <Brain className="mx-auto mb-2 h-8 w-8 animate-pulse text-blue-400" />
        Loading AI explanation...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {crisis?.is_crisis && (
        <div className="rounded-xl border-2 border-red-300 bg-red-50 p-5">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-red-600" />
            <h4 className="text-lg font-bold text-red-700">Crisis Alert</h4>
          </div>
          <ul className="mb-3 list-inside list-disc text-sm text-red-700">
            {crisis.reasons.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
          <div className="space-y-1">
            {crisis.recommended_actions.map((action, index) => (
              <p key={index} className="text-sm font-medium text-red-800">
                <span className="text-xs uppercase">[{action.priority}]</span> {action.message}
              </p>
            ))}
          </div>
        </div>
      )}

      {continuousScore !== undefined && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Stress Score</h4>
          <div className="flex items-center gap-4">
            <div className="relative h-3 flex-1 rounded-full bg-gradient-to-r from-emerald-200 via-amber-200 via-orange-200 to-red-300">
              <div
                className="absolute -top-1 h-5 w-5 rounded-full border-2 border-white bg-blue-600 shadow"
                style={{ left: `${Math.min(continuousScore, 100)}%`, transform: 'translateX(-50%)' }}
              />
            </div>
            <span className="text-2xl font-bold text-blue-700">{continuousScore.toFixed(0)}</span>
          </div>
          <div className="mt-1 flex justify-between text-xs text-slate-400">
            <span>Low</span>
            <span>Moderate</span>
            <span>High</span>
            <span>Severe</span>
          </div>
        </div>
      )}

      {explanation && explanation.top_factors && explanation.top_factors.length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-600" />
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Key Stress Factors (AI Explanation)</h4>
          </div>
          <div className="space-y-2">
            {explanation.top_factors.map((factor, index) => {
              const maxVal = Math.max(...explanation.top_factors.map((item) => Math.abs(item.shap_value || item.importance || 0)), 0.01);
              const barWidth = (Math.abs(factor.shap_value || factor.importance || 0) / maxVal) * 100;
              const isIncrease = factor.impact === 'increases_stress' || factor.impact === 'high_response';

              return (
                <div key={index}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{factor.label}</span>
                    <span className={`text-xs font-semibold ${isIncrease ? 'text-red-600' : 'text-emerald-600'}`}>
                      Response: {factor.response_value}/5 ({isIncrease ? '+' : '-'})
                    </span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${isIncrease ? 'bg-red-400' : 'bg-emerald-400'}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {Object.keys(categoryScores).length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Category Analysis</h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(categoryScores).map(([category, data]) => (
              <div key={category} className={`rounded-lg p-3 ${severityColor(data.severity)}`}>
                <p className="text-xs font-medium uppercase">{category}</p>
                <p className="text-xl font-bold">{data.average.toFixed(1)}/5</p>
                <p className="text-xs font-semibold">{data.severity}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {riskFactors.length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Identified Risk Factors</h4>
          <div className="space-y-2">
            {riskFactors.map((riskFactor, index) => (
              <div key={index} className="flex items-start gap-3 rounded-lg border border-slate-100 p-3">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-orange-500" />
                <div>
                  <p className="font-semibold text-slate-800">{riskFactor.label}</p>
                  <p className="text-sm text-slate-600">{riskFactor.message}</p>
                  <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(riskFactor.severity)}`}>
                    {riskFactor.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(probabilities).length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Prediction Probabilities</h4>
          <div className="space-y-2">
            {Object.entries(probabilities).map(([label, probability]) => (
              <div key={label}>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-700">{label}</span>
                  <span className="font-semibold text-slate-900">{(probability * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-blue-500" style={{ width: `${probability * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={handleDownloadReport}
        disabled={downloading}
        className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-500 px-5 py-2.5 text-sm font-semibold text-white shadow hover:from-blue-700 hover:to-indigo-600 disabled:opacity-50"
      >
        <Download className="h-4 w-4" />
        {downloading ? 'Generating...' : 'Download PDF Report'}
      </button>
    </div>
  );
};

export default StressExplanation;
