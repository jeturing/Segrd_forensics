import React from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const typeIcons = {
  case_created: '📁',
  analysis_complete: '✅',
  alert: '🔔',
  warning: '⚠️',
  error: '❌',
  analysis_active: '🔍',
  case_update: '📋'
};

const severityColor = {
  critical: 'bg-red-500/10 border-red-500 hover:bg-red-500/20',
  high: 'bg-orange-500/10 border-orange-500 hover:bg-orange-500/20',
  medium: 'bg-yellow-500/10 border-yellow-500 hover:bg-yellow-500/20',
  low: 'bg-blue-500/10 border-blue-500 hover:bg-blue-500/20',
  default: 'bg-gray-700/30 border-gray-600 hover:bg-gray-700/50'
};

export default function ActivityFeed({ activities }) {
  const navigate = useNavigate();

  const handleActivityClick = (activity) => {
    // Extraer case_id del mensaje (formato: "IR-XXXX-XXX: ...")
    const caseIdMatch = activity.message.match(/IR-\d{4}-\d{3}/);
    const caseId = caseIdMatch ? caseIdMatch[0] : null;

    if (caseId) {
      navigate(`/active-investigation?case=${caseId}`);
      toast.info(`Abriendo ${caseId}...`);
    } else {
      navigate('/investigations');
      toast.info('Navegando a Investigaciones...');
    }
  };

  return (
    <div className="space-y-3">
      {activities.length === 0 ? (
        <p className="text-gray-400 text-center py-8">No hay actividad reciente</p>
      ) : (
        activities.map((activity) => (
          <div
            key={activity.id}
            onClick={() => handleActivityClick(activity)}
            className={`flex gap-4 p-4 rounded-lg border-l-4 cursor-pointer transition-all transform hover:scale-102
              ${severityColor[activity.severity] || severityColor.default}
            `}
          >
            <div className="text-2xl flex-shrink-0">
              {typeIcons[activity.type] || '📌'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-gray-200 font-medium truncate">{activity.message}</p>
              <p className="text-xs text-gray-400 mt-1">
                {activity.timestamp} 
                {activity.severity && (
                  <>
                    {' • '}
                    <span className={`font-semibold ${
                      activity.severity === 'critical' ? 'text-red-400' :
                      activity.severity === 'high' ? 'text-orange-400' :
                      activity.severity === 'medium' ? 'text-yellow-400' :
                      'text-blue-400'
                    }`}>
                      {activity.severity.toUpperCase()}
                    </span>
                  </>
                )}
              </p>
            </div>
            <div className="flex-shrink-0 text-gray-400 hover:text-blue-400 transition">
              →
            </div>
          </div>
        ))
      )}
    </div>
  );
}
