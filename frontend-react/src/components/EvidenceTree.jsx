/**
 * SEGRD Security - Evidence Tree Component v4.4.1
 * Árbol jerárquico de evidencias de un caso
 */

import React, { useState, useEffect } from 'react';
import { useCaseContext } from '../context/CaseContext';

// Iconos por tipo de archivo
const FILE_ICONS = {
  folder: '📁',
  csv: '📊',
  json: '📋',
  log: '📝',
  txt: '📄',
  html: '🌐',
  pdf: '📕',
  zip: '📦',
  pcap: '🔌',
  exe: '⚙️',
  dll: '🔧',
  yara: '🎯',
  memory: '🧠',
  image: '🖼️',
  default: '📎'
};

/**
 * Obtener icono según extensión
 */
function getFileIcon(name, isDirectory) {
  if (isDirectory) return FILE_ICONS.folder;
  
  const ext = name.split('.').pop()?.toLowerCase();
  
  if (['csv', 'xlsx', 'xls'].includes(ext)) return FILE_ICONS.csv;
  if (['json'].includes(ext)) return FILE_ICONS.json;
  if (['log'].includes(ext)) return FILE_ICONS.log;
  if (['txt', 'md'].includes(ext)) return FILE_ICONS.txt;
  if (['html', 'htm'].includes(ext)) return FILE_ICONS.html;
  if (['pdf'].includes(ext)) return FILE_ICONS.pdf;
  if (['zip', 'tar', 'gz', '7z'].includes(ext)) return FILE_ICONS.zip;
  if (['pcap', 'pcapng'].includes(ext)) return FILE_ICONS.pcap;
  if (['exe', 'msi'].includes(ext)) return FILE_ICONS.exe;
  if (['dll', 'so'].includes(ext)) return FILE_ICONS.dll;
  if (['yar', 'yara'].includes(ext)) return FILE_ICONS.yara;
  if (['dmp', 'mem', 'raw'].includes(ext)) return FILE_ICONS.memory;
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp'].includes(ext)) return FILE_ICONS.image;
  
  return FILE_ICONS.default;
}

/**
 * Formatear tamaño de archivo
 */
function formatSize(bytes) {
  if (!bytes) return '-';
  
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Componente principal del árbol de evidencias
 */
export default function EvidenceTree({ caseId = null, onFileSelect = null }) {
  const { currentCase } = useCaseContext();
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  
  const effectiveCaseId = caseId || currentCase?.id;

  useEffect(() => {
    if (effectiveCaseId) {
      fetchEvidenceTree();
    }
  }, [effectiveCaseId]);

  const fetchEvidenceTree = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v41/cases/${effectiveCaseId}/evidence`, {
        headers: {
          'X-API-Key': localStorage.getItem('apiKey') || ''
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch evidence tree');
      }
      
      const data = await response.json();
      setTree(data.tree || data);
      
      // Expandir carpetas del primer nivel por defecto
      if (data.tree?.children) {
        setExpandedFolders(new Set(data.tree.children.map(c => c.path)));
      }
    } catch (err) {
      setError(err.message);
      // Datos demo si falla
      setTree(generateDemoTree(effectiveCaseId));
    } finally {
      setLoading(false);
    }
  };

  const toggleFolder = (path) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const handleFileClick = (file) => {
    setSelectedFile(file);
    if (onFileSelect) {
      onFileSelect(file);
    }
  };

  if (!effectiveCaseId) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
        <p className="text-gray-400">Select a case to view evidence</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
        <p className="text-gray-400 mt-2">Loading evidence...</p>
      </div>
    );
  }

  if (error && !tree) {
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-900 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          📂 Evidence Tree
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">
            Case: {effectiveCaseId}
          </span>
          <button
            onClick={fetchEvidenceTree}
            className="px-2 py-1 rounded text-xs bg-gray-700 hover:bg-gray-600 text-white"
          >
            🔄 Refresh
          </button>
        </div>
      </div>
      
      {/* Tree */}
      <div className="p-2 max-h-96 overflow-y-auto">
        {tree && (
          <TreeNode
            node={tree}
            level={0}
            expandedFolders={expandedFolders}
            selectedFile={selectedFile}
            onToggle={toggleFolder}
            onFileClick={handleFileClick}
          />
        )}
      </div>
      
      {/* Selected file info */}
      {selectedFile && (
        <div className="border-t border-gray-700 p-4">
          <h4 className="text-sm font-medium text-gray-400 mb-2">Selected File</h4>
          <div className="bg-gray-900 rounded p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xl">{getFileIcon(selectedFile.name, false)}</span>
              <span className="text-white font-medium">{selectedFile.name}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">Size:</span>
                <span className="text-gray-300 ml-1">{formatSize(selectedFile.size)}</span>
              </div>
              <div>
                <span className="text-gray-500">Modified:</span>
                <span className="text-gray-300 ml-1">
                  {selectedFile.modified ? new Date(selectedFile.modified).toLocaleString() : '-'}
                </span>
              </div>
            </div>
            <div className="pt-2 flex gap-2">
              <button className="px-3 py-1 rounded text-xs bg-blue-600 hover:bg-blue-700 text-white">
                👁️ Preview
              </button>
              <button className="px-3 py-1 rounded text-xs bg-green-600 hover:bg-green-700 text-white">
                📥 Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Nodo del árbol (recursivo)
 */
function TreeNode({ node, level, expandedFolders, selectedFile, onToggle, onFileClick }) {
  const isExpanded = expandedFolders.has(node.path);
  const isDirectory = node.type === 'directory' || node.children;
  const isSelected = selectedFile?.path === node.path;
  
  const paddingLeft = level * 16;
  
  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1 px-2 rounded cursor-pointer hover:bg-gray-700 ${
          isSelected ? 'bg-blue-900/50 border border-blue-500' : ''
        }`}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={() => {
          if (isDirectory) {
            onToggle(node.path);
          } else {
            onFileClick(node);
          }
        }}
      >
        {/* Expand/collapse icon for directories */}
        {isDirectory && (
          <span className="text-gray-500 w-4">
            {isExpanded ? '▼' : '▶'}
          </span>
        )}
        {!isDirectory && <span className="w-4" />}
        
        {/* File/folder icon */}
        <span className="text-lg">{getFileIcon(node.name, isDirectory)}</span>
        
        {/* Name */}
        <span className={`flex-1 truncate ${isDirectory ? 'text-blue-400' : 'text-gray-300'}`}>
          {node.name}
        </span>
        
        {/* Size for files */}
        {!isDirectory && node.size && (
          <span className="text-xs text-gray-500">{formatSize(node.size)}</span>
        )}
        
        {/* Children count for directories */}
        {isDirectory && node.children && (
          <span className="text-xs text-gray-500">({node.children.length})</span>
        )}
      </div>
      
      {/* Children */}
      {isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child, index) => (
            <TreeNode
              key={child.path || index}
              node={child}
              level={level + 1}
              expandedFolders={expandedFolders}
              selectedFile={selectedFile}
              onToggle={onToggle}
              onFileClick={onFileClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Generar árbol demo para testing
 */
function generateDemoTree(caseId) {
  return {
    name: caseId,
    path: `/evidence/${caseId}`,
    type: 'directory',
    children: [
      {
        name: 'sparrow',
        path: `/evidence/${caseId}/sparrow`,
        type: 'directory',
        children: [
          { name: 'sign_ins.csv', path: `/evidence/${caseId}/sparrow/sign_ins.csv`, size: 45678, modified: '2025-01-15T10:30:00Z' },
          { name: 'oauth_apps.json', path: `/evidence/${caseId}/sparrow/oauth_apps.json`, size: 12340, modified: '2025-01-15T10:31:00Z' },
          { name: 'audit_logs.csv', path: `/evidence/${caseId}/sparrow/audit_logs.csv`, size: 234567, modified: '2025-01-15T10:32:00Z' }
        ]
      },
      {
        name: 'loki',
        path: `/evidence/${caseId}/loki`,
        type: 'directory',
        children: [
          { name: 'scan_results.json', path: `/evidence/${caseId}/loki/scan_results.json`, size: 89012, modified: '2025-01-15T11:00:00Z' },
          { name: 'yara_matches.txt', path: `/evidence/${caseId}/loki/yara_matches.txt`, size: 5678, modified: '2025-01-15T11:01:00Z' }
        ]
      },
      {
        name: 'memory',
        path: `/evidence/${caseId}/memory`,
        type: 'directory',
        children: [
          { name: 'memdump.dmp', path: `/evidence/${caseId}/memory/memdump.dmp`, size: 4294967296, modified: '2025-01-15T09:00:00Z' },
          { name: 'pslist.json', path: `/evidence/${caseId}/memory/pslist.json`, size: 45678, modified: '2025-01-15T09:15:00Z' },
          { name: 'netscan.json', path: `/evidence/${caseId}/memory/netscan.json`, size: 23456, modified: '2025-01-15T09:16:00Z' }
        ]
      },
      {
        name: 'network',
        path: `/evidence/${caseId}/network`,
        type: 'directory',
        children: [
          { name: 'capture.pcap', path: `/evidence/${caseId}/network/capture.pcap`, size: 15728640, modified: '2025-01-15T08:00:00Z' }
        ]
      },
      {
        name: 'reports',
        path: `/evidence/${caseId}/reports`,
        type: 'directory',
        children: [
          { name: 'executive_summary.pdf', path: `/evidence/${caseId}/reports/executive_summary.pdf`, size: 234567, modified: '2025-01-15T14:00:00Z' },
          { name: 'technical_report.html', path: `/evidence/${caseId}/reports/technical_report.html`, size: 456789, modified: '2025-01-15T14:30:00Z' }
        ]
      }
    ]
  };
}
