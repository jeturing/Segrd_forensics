/**
 * Reports Page - v4.5
 * Generación de reportes PDF/HTML para investigaciones
 * 
 * v4.4: Integración con CaseContext - case_id obligatorio
 * v4.5: Barra de progreso visual + Opciones de descarga/compartir
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText, Download, Plus, Eye, Trash2, RefreshCw,
  Clock, CheckCircle, AlertCircle, File, FileCode, 
  FileType, Layers, Brain, Send, Loader2
} from 'lucide-react';
import api from '../../services/api';
import { API_BASE_URL } from '../../services/api';
import { useCaseContext } from '../../context/CaseContext';
import CaseHeader from '../CaseHeader';

// Templates disponibles
const REPORT_TEMPLATES = {
  technical: {
    name: 'Reporte Técnico',
    description: 'Análisis técnico detallado con IOCs, timeline y metodología',
    icon: FileCode,
    color: 'text-blue-400',
    sections: ['executive_summary', 'scope', 'methodology', 'findings', 'iocs', 'timeline', 'recommendations']
  },
  executive: {
    name: 'Reporte Ejecutivo',
    description: 'Resumen de alto nivel para stakeholders',
    icon: FileText,
    color: 'text-purple-400',
    sections: ['executive_summary', 'impact_assessment', 'risk_level', 'key_findings', 'recommendations']
  },
  evidence: {
    name: 'Reporte de Evidencia',
    description: 'Cadena de custodia y artefactos recolectados',
    icon: File,
    color: 'text-green-400',
    sections: ['case_info', 'evidence_chain', 'artifacts', 'timeline', 'iocs']
  },
  incident: {
    name: 'Reporte de Incidente',
    description: 'Documentación del ciclo de respuesta IR',
    icon: AlertCircle,
    color: 'text-orange-400',
    sections: ['incident_summary', 'detection', 'containment', 'eradication', 'recovery', 'lessons_learned']
  }
};

// Formatos de salida
const OUTPUT_FORMATS = [
  { id: 'pdf', name: 'PDF', icon: FileType },
  { id: 'html', name: 'HTML', icon: FileCode },
  { id: 'json', name: 'JSON', icon: File },
  { id: 'md', name: 'Markdown', icon: FileText }
];

const LANGUAGES = [
  { id: 'es', name: 'Español' },
  { id: 'en', name: 'English' },
  { id: 'zh-CN', name: '中文 (简体)' },
  { id: 'zh-HK', name: '中文 (繁體)' }
];

const ReportsPage = () => {
  // v4.4: Usar contexto de caso
  const { currentCase, hasActiveCase, getCaseId, registerActivity } = useCaseContext();
  
  const [reports, setReports] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showGenerator, setShowGenerator] = useState(false);
  const [previewReport, setPreviewReport] = useState(null);
  const [actionModal, setActionModal] = useState({ open: false, type: null, report: null });
  
  // v4.5: Estado de progreso de generación
  const [generationProgress, setGenerationProgress] = useState({
    show: false,
    reportId: null,
    progress: 0,
    currentStep: 'Iniciando...',
    status: 'generating',
    downloadUrl: null,
    shareUrl: null
  });
  
  // Estado del generador
  const [generator, setGenerator] = useState({
    report_type: 'technical',
    format: 'pdf',
    title: '',
    include_sections: [],
    use_llm: true,
    include_raw: false,
    language: 'es',
    auto_ingest: true
  });

  // Cargar reportes - v4.4: Usa case_id del contexto
  const loadReports = useCallback(async () => {
    if (!hasActiveCase()) return;
    
    const caseId = getCaseId();
    
    try {
      setLoading(true);
      registerActivity('reports_loaded', { case_id: caseId });
      
      const [reportsRes, templatesRes] = await Promise.all([
        api.get(`/reports/case/${caseId}`),
        api.get('/reports/templates')
      ]);
      setReports(reportsRes.data.reports || []);
      setTemplates(templatesRes.data.templates || Object.keys(REPORT_TEMPLATES));
    } catch (error) {
      console.error('Error loading reports:', error);
      // Datos de ejemplo
      setReports([
        {
          report_id: 'rpt_001',
          title: 'Reporte Técnico - BEC Investigation',
          report_type: 'technical',
          format: 'pdf',
          status: 'completed',
          created_at: '2025-12-07T10:00:00Z',
          file_size: 2456000,
          llm_generated: true,
          language: 'es',
          auto_ingest: true
        },
        {
          report_id: 'rpt_002',
          title: 'Resumen Ejecutivo Q4',
          report_type: 'executive',
          format: 'pdf',
          status: 'completed',
          created_at: '2025-12-06T15:30:00Z',
          file_size: 1234000,
          llm_generated: true,
          language: 'en',
          auto_ingest: false
        }
      ]);
    } finally {
      setLoading(false);
    }
  }, [hasActiveCase, getCaseId, registerActivity]);

  // v4.4: Recargar cuando cambie el caso
  useEffect(() => {
    if (hasActiveCase()) {
      loadReports();
    }
  }, [currentCase, loadReports, hasActiveCase]);

  // v4.6: Generar título automático basado en caso y tipo
  const generateAutoTitle = useCallback(() => {
    if (!hasActiveCase()) return '';
    const caseId = getCaseId();
    const templateName = REPORT_TEMPLATES[generator.report_type]?.name || 'Reporte';
    const date = new Date().toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
    return `${templateName} - ${caseId} - ${date}`;
  }, [hasActiveCase, getCaseId, generator.report_type]);

  // v4.6: Auto-generar título cuando cambia el tipo de reporte
  useEffect(() => {
    if (hasActiveCase() && !generator.title) {
      setGenerator(prev => ({ ...prev, title: generateAutoTitle() }));
    }
  }, [generator.report_type, hasActiveCase, generateAutoTitle]);

  // v4.6: Actualizar título cuando se abre el generador
  useEffect(() => {
    if (showGenerator && hasActiveCase()) {
      setGenerator(prev => ({ ...prev, title: generateAutoTitle() }));
    }
  }, [showGenerator, hasActiveCase, generateAutoTitle]);

  // Generar reporte - v4.6: Con barra de progreso visual y animaciones
  const generateReport = async () => {
    if (!hasActiveCase()) {
      alert('Por favor selecciona un caso primero');
      return;
    }

    const caseId = getCaseId();
    // v4.6: Auto-generar título si está vacío
    const reportTitle = generator.title || generateAutoTitle();

    try {
      setGenerating(true);
      registerActivity('report_generated', { title: reportTitle, type: generator.report_type });
      
      const response = await api.post('/reports/generate', {
        case_id: caseId,
        report_type: generator.report_type,
        format: generator.format,
        title: reportTitle,
        include_sections: generator.include_sections.length > 0 ? generator.include_sections : null,
        use_llm_summary: generator.use_llm,
        include_raw_evidence: generator.include_raw,
        language: generator.language,
        auto_ingest: generator.auto_ingest
      });

      // v4.6: Mostrar modal de progreso con animaciones
      const reportId = response.data.report_id;
      setGenerationProgress({
        show: true,
        reportId,
        progress: 5,
        currentStep: 'Iniciando generación...',
        status: 'generating',
        downloadUrl: null,
        shareUrl: null,
        title: generator.title,
        format: generator.format
      });
      setShowGenerator(false);

      // Polling para status con actualización de progreso
      const pollStatus = async () => {
        try {
          const statusRes = await api.get(`/reports/${reportId}/status`);
          const data = statusRes.data;
          
          setGenerationProgress(prev => ({
            ...prev,
            progress: data.progress || prev.progress,
            currentStep: data.current_step || prev.currentStep,
            status: data.status
          }));
          
          if (data.status === 'completed') {
            setGenerationProgress(prev => ({
              ...prev,
              progress: 100,
              currentStep: '¡Reporte completado!',
              status: 'completed',
              downloadUrl: data.download_url || `/reports/${reportId}/download`,
              shareUrl: data.share_url || `/reports/${reportId}/share`
            }));
            loadReports();
            setGenerator({
              report_type: 'technical',
              format: 'pdf',
              title: '',
              include_sections: [],
              use_llm: true,
              include_raw: false,
              language: 'es',
              auto_ingest: true
            });
          } else if (data.status === 'failed') {
            setGenerationProgress(prev => ({
              ...prev,
              status: 'failed',
              currentStep: 'Error en la generación'
            }));
          } else if (data.status === 'generating') {
            setTimeout(pollStatus, 1000); // Polling más frecuente
          }
        } catch (error) {
          console.error('Error polling status:', error);
          setGenerationProgress(prev => ({
            ...prev,
            status: 'failed',
            currentStep: 'Error de conexión'
          }));
        }
      };
      
      setTimeout(pollStatus, 1000);
      
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Error generando reporte');
    } finally {
      setGenerating(false);
    }
  };

  // v4.5: Copiar link de compartir
  const copyShareLink = async (reportId) => {
    const shareUrl = `${window.location.origin}/reports/${reportId}/view`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      alert('Link copiado al portapapeles');
    } catch (err) {
      // Fallback para navegadores sin clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = shareUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('Link copiado al portapapeles');
    }
  };

  // v4.5: Cerrar modal de progreso
  const closeProgressModal = () => {
    setGenerationProgress({
      show: false,
      reportId: null,
      progress: 0,
      currentStep: 'Iniciando...',
      status: 'generating',
      downloadUrl: null,
      shareUrl: null
    });
  };

  // Descargar reporte
  const downloadReport = async (reportId) => {
    try {
      const response = await api.get(`/reports/${reportId}/download`, {
        responseType: 'blob'
      });
      
      const report = reports.find(r => r.report_id === reportId);
      const filename = `${report?.title || 'report'}.${report?.format || 'pdf'}`;
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading report:', error);
    }
  };

  // Eliminar reporte
  const deleteReport = async (reportId) => {
    try {
      await api.delete(`/reports/${reportId}`);
      loadReports();
    } catch (error) {
      console.error('Error deleting report:', error);
    }
  };

  // Preview reporte - v4.4: Usa case_id del contexto
  const previewReportFn = async () => {
    if (!hasActiveCase()) return;
    
    try {
      const response = await api.post('/reports/preview', {
        case_id: getCaseId(),
        report_type: generator.report_type,
        include_sections: generator.include_sections.length > 0 ? generator.include_sections : null,
        language: generator.language
      });
      setPreviewReport(response.data);
    } catch (error) {
      console.error('Error previewing report:', error);
    }
  };

  // Formatear tamaño de archivo
  const formatFileSize = (bytes) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Formatear fecha
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const templateList = templates.length
    ? templates
    : Object.entries(REPORT_TEMPLATES).map(([id, tpl]) => ({ id, ...tpl }));

  const openActionModal = (type, report) => {
    setActionModal({ open: true, type, report });
  };

  const closeActionModal = () => {
    setActionModal({ open: false, type: null, report: null });
  };

  const confirmAction = async () => {
    if (!actionModal.report) return;
    if (actionModal.type === 'download') {
      await downloadReport(actionModal.report.report_id);
    } else if (actionModal.type === 'delete') {
      await deleteReport(actionModal.report.report_id);
    }
    closeActionModal();
  };

  if (loading && hasActiveCase()) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* v4.4: Case Header */}
      <CaseHeader 
        title="Reportes"
        subtitle={hasActiveCase() ? `${reports.length} reportes generados` : 'Selecciona un caso'}
        icon="📄"
      />
      
      {/* v4.4: Solo mostrar contenido si hay caso */}
      {!hasActiveCase() ? (
        <div className="flex items-center justify-center h-64 text-gray-500">
          Selecciona un caso para gestionar reportes
        </div>
      ) : (
      <>
      {/* Header con acciones */}
      <div className="flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <FileText className="w-8 h-8 text-amber-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">Reportes</h1>
            <p className="text-gray-400 text-sm">
              Caso: <span className="text-amber-400">{getCaseId()}</span> • {reports.length} reportes
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowGenerator(true)}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nuevo Reporte
          </button>
          <button
            onClick={loadReports}
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Report Generator Modal */}
      {showGenerator && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-6">Generar Nuevo Reporte</h3>
            
            {/* Template Selection */}
            <div className="mb-6">
              <label className="block text-sm text-gray-400 mb-3">Tipo de Reporte</label>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(REPORT_TEMPLATES).map(([id, template]) => {
                  const IconComponent = template.icon;
                  return (
                    <button
                      key={id}
                      onClick={() => setGenerator({...generator, report_type: id})}
                      className={`p-4 rounded-lg border text-left transition-colors ${
                        generator.report_type === id
                          ? 'border-amber-500 bg-amber-500/10'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <IconComponent className={`w-6 h-6 ${template.color}`} />
                        <div>
                          <div className="font-medium text-white">{template.name}</div>
                          <div className="text-xs text-gray-400">{template.description}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Title */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-1">Título del Reporte</label>
              <input
                type="text"
                value={generator.title}
                onChange={(e) => setGenerator({...generator, title: e.target.value})}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                placeholder="Ej: Reporte de Incidente BEC - Diciembre 2025"
              />
            </div>

            {/* Format Selection */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">Formato de Salida</label>
              <div className="flex gap-2">
                {OUTPUT_FORMATS.map(format => (
                  <button
                    key={format.id}
                    onClick={() => setGenerator({...generator, format: format.id})}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      generator.format === format.id
                        ? 'bg-amber-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    <format.icon className="w-4 h-4" />
                    {format.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Language & automation */}
            <div className="mb-4 grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Idioma del Reporte</label>
                <div className="flex gap-2 flex-wrap">
                  {LANGUAGES.map(lang => (
                    <button
                      key={lang.id}
                      onClick={() => setGenerator({ ...generator, language: lang.id })}
                      className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                        generator.language === lang.id
                          ? 'border-amber-500 bg-amber-500/10 text-white'
                          : 'border-gray-700 text-gray-300 hover:border-gray-500'
                      }`}
                    >
                      {lang.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-lg border border-gray-700 bg-gray-900/60">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={generator.auto_ingest}
                    onChange={(e) => setGenerator({ ...generator, auto_ingest: e.target.checked })}
                    className="mt-1 rounded bg-gray-700 border-gray-600 text-amber-600 focus:ring-amber-500"
                  />
                  <div>
                    <div className="flex items-center gap-2 text-white font-medium">
                      <Layers className="w-4 h-4 text-amber-400" />
                      Autogenerar con evidencia
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Analiza los artefactos del caso y arma el caso en el idioma elegido.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Sections */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">
                Secciones a Incluir 
                <span className="text-xs ml-2">(dejar vacío para todas)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {REPORT_TEMPLATES[generator.report_type]?.sections.map(section => (
                  <button
                    key={section}
                    onClick={() => {
                      const sections = generator.include_sections.includes(section)
                        ? generator.include_sections.filter(s => s !== section)
                        : [...generator.include_sections, section];
                      setGenerator({...generator, include_sections: sections});
                    }}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      generator.include_sections.includes(section)
                        ? 'bg-amber-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {section.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div className="mb-6 space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={generator.use_llm}
                  onChange={(e) => setGenerator({...generator, use_llm: e.target.checked})}
                  className="rounded bg-gray-700 border-gray-600 text-amber-600 focus:ring-amber-500"
                />
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span className="text-white">Generar resumen con LLM</span>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={generator.include_raw}
                  onChange={(e) => setGenerator({...generator, include_raw: e.target.checked})}
                  className="rounded bg-gray-700 border-gray-600 text-amber-600 focus:ring-amber-500"
                />
                <span className="text-white">Incluir datos raw en apéndice</span>
              </label>
            </div>

            {/* Preview */}
            {previewReport && (
              <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Vista Previa</h4>
                <div
                  dangerouslySetInnerHTML={{ __html: previewReport.preview_html || previewReport.html || '' }}
                  className="prose prose-invert max-w-none text-sm"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Páginas estimadas: {previewReport.estimated_pages}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-between">
              <button
                onClick={previewReportFn}
                className="flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors"
              >
                <Eye className="w-4 h-4" />
                Vista Previa
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowGenerator(false);
                    setPreviewReport(null);
                  }}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={generateReport}
                  disabled={generating || !generator.title}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg transition-colors"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Generar
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reports List */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Reporte</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Tipo</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Formato</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Idioma</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Estado</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Tamaño</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Creado</th>
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-400">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {reports.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-8 text-center text-gray-400">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No hay reportes generados</p>
                  <button
                    onClick={() => setShowGenerator(true)}
                    className="mt-2 text-amber-400 hover:text-amber-300"
                  >
                    Generar primer reporte
                  </button>
                </td>
              </tr>
            ) : (
              reports.map(report => {
                const template = REPORT_TEMPLATES[report.report_type];
                const IconComponent = template?.icon || FileText;
                
                return (
                  <tr key={report.report_id} className="hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <IconComponent className={`w-5 h-5 ${template?.color || 'text-gray-400'}`} />
                        <div>
                          <div className="font-medium text-white">{report.title}</div>
                          {report.llm_generated && (
                            <div className="flex items-center gap-1 text-xs text-purple-400">
                              <Brain className="w-3 h-3" />
                              LLM Generated
                            </div>
                          )}
                          {report.auto_ingest && (
                            <div className="flex items-center gap-1 text-xs text-amber-400">
                              <Layers className="w-3 h-3" />
                              Auto evidencia
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="capitalize text-gray-300">{report.report_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="uppercase text-xs bg-gray-700 px-2 py-1 rounded">
                        {report.format}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-300 uppercase text-xs bg-gray-700 px-2 py-1 rounded">
                        {report.language || 'es'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1 text-sm ${
                        report.status === 'completed' ? 'text-green-400' :
                        report.status === 'generating' ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {report.status === 'completed' && <CheckCircle className="w-4 h-4" />}
                        {report.status === 'generating' && <Clock className="w-4 h-4 animate-pulse" />}
                        {report.status === 'failed' && <AlertCircle className="w-4 h-4" />}
                        {report.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {formatFileSize(report.file_size)}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {formatDate(report.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {report.status === 'completed' && (
                          <button
                            onClick={() => openActionModal('download', report)}
                            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                            title="Descargar"
                          >
                            <Download className="w-4 h-4 text-gray-400 hover:text-amber-400" />
                          </button>
                        )}
                        <button
                          onClick={() => openActionModal('delete', report)}
                          className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Template Cards */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Templates Disponibles</h2>
        <div className="grid grid-cols-4 gap-4">
          {templateList.map((template) => {
            const IconComponent = REPORT_TEMPLATES[template.id]?.icon || FileText;
            const color = REPORT_TEMPLATES[template.id]?.color || template.color || 'text-gray-300';
            const sections = template.sections || REPORT_TEMPLATES[template.id]?.sections || [];
            return (
              <div
                key={template.id}
                className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={`p-2 rounded-lg bg-gray-700`}>
                    <IconComponent className={`w-6 h-6 ${color}`} />
                  </div>
                  <h3 className="font-medium text-white">{template.name}</h3>
                </div>
                <p className="text-sm text-gray-400 mb-3">{template.description || REPORT_TEMPLATES[template.id]?.description}</p>
                <div className="flex flex-wrap gap-1">
                  {sections.slice(0, 3).map(section => (
                    <span key={section} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                      {section.replace('_', ' ')}
                    </span>
                  ))}
                  {sections.length > 3 && (
                    <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded">
                      +{sections.length - 3} más
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* v4.6: Modal de Progreso de Generación con animaciones Purple Team */}
      {generationProgress.show && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-8 w-full max-w-lg border border-purple-700/50 shadow-2xl bounce-in relative overflow-hidden">
            
            {/* v4.6: Scan line animation durante generación */}
            {generationProgress.status === 'generating' && (
              <div className="scan-line" />
            )}
            
            {/* v4.6: Purple Team gradient border effect */}
            <div className="absolute inset-0 rounded-xl pointer-events-none" 
              style={{ 
                background: generationProgress.status === 'generating' 
                  ? 'linear-gradient(135deg, rgba(168,85,247,0.1) 0%, transparent 50%, rgba(168,85,247,0.1) 100%)'
                  : 'transparent'
              }} 
            />
            
            {/* Header */}
            <div className="text-center mb-6 relative z-10">
              <div className={`inline-flex p-4 rounded-full mb-4 ${
                generationProgress.status === 'completed' ? 'bg-green-500/20' :
                generationProgress.status === 'failed' ? 'bg-red-500/20' :
                'bg-purple-500/20 query-pulse'
              }`}>
                {generationProgress.status === 'completed' ? (
                  <CheckCircle className="w-12 h-12 text-green-400 bounce-in" />
                ) : generationProgress.status === 'failed' ? (
                  <AlertCircle className="w-12 h-12 text-red-400" />
                ) : (
                  <Brain className="w-12 h-12 text-purple-400 ai-glow" />
                )}
              </div>
              <h3 className="text-xl font-bold text-white">
                {generationProgress.status === 'completed' ? '¡Reporte Generado!' :
                 generationProgress.status === 'failed' ? 'Error en Generación' :
                 'Analizando con Purple Team...'}
              </h3>
              {generationProgress.title && (
                <p className="text-gray-400 mt-1">{generationProgress.title}</p>
              )}
              
              {/* v4.6: Indicador de LLM activo */}
              {generationProgress.status === 'generating' && generator.use_llm && (
                <div className="flex items-center justify-center gap-2 mt-3 text-purple-400 text-sm">
                  <Brain className="w-4 h-4 network-pulse" />
                  <span>LLM enriqueciendo informe</span>
                  <span className="flex gap-0.5">
                    <span className="typing-dot w-1.5 h-1.5 bg-purple-400 rounded-full"></span>
                    <span className="typing-dot w-1.5 h-1.5 bg-purple-400 rounded-full"></span>
                    <span className="typing-dot w-1.5 h-1.5 bg-purple-400 rounded-full"></span>
                  </span>
                </div>
              )}
              
              {/* v4.6: Indicador de modo template (sin LLM) */}
              {generationProgress.status === 'generating' && !generator.use_llm && (
                <div className="flex items-center justify-center gap-2 mt-3 text-amber-400 text-sm">
                  <FileCode className="w-4 h-4" />
                  <span>Generando desde template</span>
                </div>
              )}
            </div>

            {/* Barra de Progreso con animación mejorada */}
            <div className="mb-6 relative z-10">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-400">{generationProgress.currentStep}</span>
                <span className="text-purple-400 font-mono">{generationProgress.progress}%</span>
              </div>
              <div className="h-3 bg-gray-700 rounded-full overflow-hidden relative">
                <div 
                  className={`h-full transition-all duration-500 ease-out rounded-full ${
                    generationProgress.status === 'completed' ? 'bg-gradient-to-r from-green-500 to-green-400' :
                    generationProgress.status === 'failed' ? 'bg-red-500' :
                    'bg-gradient-to-r from-purple-600 via-purple-500 to-purple-400'
                  }`}
                  style={{ width: `${generationProgress.progress}%` }}
                />
                {generationProgress.status === 'generating' && (
                  <div className="absolute inset-0 shimmer" />
                )}
              </div>
            </div>

            {/* Botones de Acción - Solo cuando está completado */}
            {generationProgress.status === 'completed' && (
              <div className="space-y-3 slide-up-fade relative z-10">
                <div className="grid grid-cols-2 gap-3">
                  {/* Descargar - v4.6: Usa función con autenticación */}
                  <button
                    onClick={() => {
                      downloadReport(generationProgress.reportId);
                      closeProgressModal();
                    }}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-medium transition-all transform hover:scale-[1.02]"
                  >
                    <Download className="w-5 h-5" />
                    Descargar
                  </button>
                  
                  {/* Copiar Link */}
                  <button
                    onClick={() => copyShareLink(generationProgress.reportId)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-white font-medium transition-colors"
                  >
                    <Send className="w-5 h-5" />
                    Copiar Link
                  </button>
                </div>

                {/* Ver Reporte - v4.6: Usa función con autenticación */}
                <button
                  onClick={async () => {
                    try {
                      const response = await api.get(`/reports/${generationProgress.reportId}/download`, {
                        responseType: 'blob'
                      });
                      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/html' }));
                      window.open(url, '_blank');
                      closeProgressModal();
                    } catch (error) {
                      console.error('Error opening report:', error);
                      alert('Error al abrir el reporte');
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-gray-600 hover:border-gray-500 text-gray-300 hover:text-white transition-colors"
                >
                  <Eye className="w-5 h-5" />
                  Ver en Nueva Pestaña
                </button>

                {/* Cerrar */}
                <button
                  onClick={closeProgressModal}
                  className="w-full text-gray-500 hover:text-gray-300 text-sm py-2 transition-colors"
                >
                  Cerrar
                </button>
              </div>
            )}

            {/* Botón de cerrar para errores */}
            {generationProgress.status === 'failed' && (
              <div className="space-y-3">
                <button
                  onClick={closeProgressModal}
                  className="w-full px-4 py-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-white font-medium transition-colors"
                >
                  Cerrar
                </button>
              </div>
            )}

            {/* Info adicional mientras genera */}
            {generationProgress.status === 'generating' && (
              <div className="text-center text-gray-500 text-sm">
                <p>Este proceso puede tomar unos segundos...</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Modal */}
      {actionModal.open && actionModal.report && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {actionModal.type === 'download' ? 'Descargar reporte' : 'Eliminar reporte'}
                </h3>
                <p className="text-sm text-gray-400 mt-1">{actionModal.report.title}</p>
              </div>
              <button onClick={closeActionModal} className="text-gray-400 hover:text-white">✕</button>
            </div>

            {actionModal.type === 'download' ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-300">
                  Puedes abrir el archivo directo o usar la descarga con fallback.
                </p>
                <a
                  href={`${API_BASE_URL}/reports/${actionModal.report.report_id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full text-center px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white transition-colors"
                >
                  Abrir/Descargar
                </a>
                <button
                  onClick={confirmAction}
                  className="w-full px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
                >
                  Reintentar con fallback JS
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-300">
                  Esta acción eliminará el archivo generado.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={closeActionModal}
                    className="flex-1 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={confirmAction}
                    className="flex-1 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      </>
      )}
    </div>
  );
};

export default ReportsPage;
