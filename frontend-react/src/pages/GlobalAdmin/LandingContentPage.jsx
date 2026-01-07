/* eslint-disable react/prop-types */
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, ArrowLeft, Save, RefreshCw, Globe, Layers, Star, ListChecks, Quote, Puzzle } from 'lucide-react';
import api from '../../services/api';

export default function LandingContentPage() {
  const navigate = useNavigate();
  const [locale, setLocale] = useState('es');
  const [activeTab, setActiveTab] = useState('plans');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState({ plans: { items: [] }, features: { items: [] }, testimonials: { items: [] }, stats: { items: [] }, integrations: { items: [] }, capabilities: { items: [] } });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    const doLoad = async () => {
      setLoading(true); setError(null);
      try {
        const res = await api.get('/api/global-admin/landing', { params: { locale } });
        setData({
          plans: res.data?.data?.plans || { items: [] },
          features: res.data?.data?.features || { items: [] },
          testimonials: res.data?.data?.testimonials || { items: [] },
          stats: res.data?.data?.stats || { items: [] },
          integrations: res.data?.data?.integrations || { items: [] },
          capabilities: res.data?.data?.capabilities || { items: [] }
        });
      } catch (e) {
        setError(e.response?.data?.detail || 'Error cargando contenido');
      } finally {
        setLoading(false);
      }
    };
    doLoad();
  }, [locale]);

  const handleItemsChange = (section, items) => {
    setData(prev => ({ ...prev, [section]: { items } }));
    setSuccess(null);
  };

  const addItem = (section, template) => {
    const items = [...(data[section]?.items || []), template];
    handleItemsChange(section, items);
  };

  const removeItem = (section, idx) => {
    const items = (data[section]?.items || []).filter((_, i) => i !== idx);
    handleItemsChange(section, items);
  };

  const saveSection = async (section) => {
    setSaving(true); setError(null); setSuccess(null);
    try {
      await api.put(`/api/global-admin/landing/${section}`, { items: data[section].items }, { params: { locale } });
      setSuccess('Cambios guardados');
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const SectionHeader = ({ icon: Icon, title, section }) => (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2"><Icon className="w-5 h-5 text-blue-400" /><h2 className="text-xl font-semibold text-white">{title}</h2></div>
      <div className="flex items-center gap-3">
        <button onClick={() => saveSection(section)} disabled={saving} className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm flex items-center gap-2">
          {saving ? <RefreshCw className="w-4 h-4 animate-spin"/> : <Save className="w-4 h-4"/>}
          Guardar
        </button>
      </div>
    </div>
  );

  const TextInput = ({ value, onChange, placeholder }) => (
    <input className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
  );

  const TextArea = ({ value, onChange, placeholder }) => (
    <textarea rows={3} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
  );

  // NumberInput no usado por ahora

  const FeatureCard = ({ item, onChange, onRemove }) => (
    <div className="p-4 bg-gray-800 border border-gray-700 rounded-xl space-y-2">
      <TextInput value={item.title || ''} onChange={v => onChange({ ...item, title: v })} placeholder="Título" />
      <TextArea value={item.description || ''} onChange={v => onChange({ ...item, description: v })} placeholder="Descripción" />
      <div className="space-y-2">
        <label className="text-sm text-gray-400">Highlights (coma-separado)</label>
        <TextInput value={(item.highlights || []).join(', ')} onChange={v => onChange({ ...item, highlights: v.split(',').map(s => s.trim()).filter(Boolean) })} placeholder="A, B, C" />
      </div>
      <button onClick={onRemove} className="mt-2 text-red-400 hover:text-red-300 text-sm">Eliminar</button>
    </div>
  );

  const PlanCard = ({ item, onChange, onRemove }) => (
    <div className={`p-4 bg-gray-800 border border-gray-700 rounded-xl space-y-2`}>
      <div className="grid grid-cols-2 gap-3">
        <TextInput value={item.name || ''} onChange={v => onChange({ ...item, name: v })} placeholder="Nombre" />
        <TextInput value={item.price || ''} onChange={v => onChange({ ...item, price: v })} placeholder="Precio" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <TextInput value={item.period || ''} onChange={v => onChange({ ...item, period: v })} placeholder="/mes" />
        <TextInput value={item.cta || ''} onChange={v => onChange({ ...item, cta: v })} placeholder="CTA" />
      </div>
      <TextArea value={item.description || ''} onChange={v => onChange({ ...item, description: v })} placeholder="Descripción" />
      <div className="space-y-2">
        <label className="text-sm text-gray-400">Features (una por línea)</label>
        <TextArea value={(item.features || []).join('\n')} onChange={v => onChange({ ...item, features: v.split('\n').map(s => s.trim()).filter(Boolean) })} />
      </div>
      <div className="flex items-center gap-2 text-sm text-gray-300">
        <label className="flex items-center gap-2"><input type="checkbox" checked={!!item.highlighted} onChange={e => onChange({ ...item, highlighted: e.target.checked })} /> Popular</label>
      </div>
      <button onClick={onRemove} className="mt-2 text-red-400 hover:text-red-300 text-sm">Eliminar</button>
    </div>
  );

  if (loading) return (
    <div className="min-h-screen bg-gray-900 p-6 text-gray-400">Cargando...</div>
  );

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/admin')} className="p-2 hover:bg-gray-800 rounded-lg transition-colors"><ArrowLeft className="w-5 h-5 text-gray-400"/></button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Settings className="w-7 h-7 text-orange-400"/>Contenido del Landing</h1>
            <p className="text-gray-400 text-sm">Edita planes, features, testimonios y más</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select value={locale} onChange={e => setLocale(e.target.value)} className="px-3 py-2 bg-gray-800 border border-gray-700 text-white rounded-lg">
            <option value="es">Español (es)</option>
            <option value="en">English (en)</option>
          </select>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 text-green-400 rounded-lg">{success}</div>}

      <div className="flex gap-6">
        <div className="w-64 bg-gray-800 rounded-xl p-4 border border-gray-700 h-fit">
          {[
            { id: 'plans', label: 'Planes', icon: Layers },
            { id: 'features', label: 'Features', icon: ListChecks },
            { id: 'testimonials', label: 'Testimonios', icon: Quote },
            { id: 'stats', label: 'Estadísticas', icon: Star },
            { id: 'integrations', label: 'Integraciones', icon: Puzzle },
            { id: 'capabilities', label: 'Capacidades', icon: Globe }
          ].map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${activeTab === tab.id ? 'bg-blue-600 text-white':'text-gray-400 hover:bg-gray-700 hover:text-white'}`}>
              <tab.icon className="w-5 h-5"/>{tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-gray-800 rounded-xl p-6 border border-gray-700">
          {activeTab === 'features' && (
            <div>
              <SectionHeader icon={ListChecks} title="Features" section="features"/>
              <div className="grid md:grid-cols-2 gap-4">
                {(data.features.items || []).map((item, idx) => (
                  <FeatureCard key={idx} item={item} onChange={it => {
                    const items = [...data.features.items]; items[idx] = it; handleItemsChange('features', items);
                  }} onRemove={() => removeItem('features', idx)} />
                ))}
              </div>
              <button onClick={() => addItem('features', { title: '', description: '', highlights: [] })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Feature</button>
            </div>
          )}

          {activeTab === 'plans' && (
            <div>
              <SectionHeader icon={Layers} title="Planes" section="plans"/>
              <div className="grid md:grid-cols-2 gap-4">
                {(data.plans.items || []).map((item, idx) => (
                  <PlanCard key={idx} item={item} onChange={it => { const items = [...data.plans.items]; items[idx] = it; handleItemsChange('plans', items); }} onRemove={() => removeItem('plans', idx)} />
                ))}
              </div>
              <button onClick={() => addItem('plans', { name: '', price: '', period: '', description: '', features: [], cta: 'Comenzar', highlighted: false })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Plan</button>
            </div>
          )}

          {activeTab === 'testimonials' && (
            <div>
              <SectionHeader icon={Quote} title="Testimonios" section="testimonials"/>
              <div className="space-y-3">
                {(data.testimonials.items || []).map((item, idx) => (
                  <div key={idx} className="p-4 bg-gray-800 border border-gray-700 rounded-xl space-y-2">
                    <TextArea value={item.quote || ''} onChange={v => { const it = { ...item, quote: v }; const items = [...data.testimonials.items]; items[idx] = it; handleItemsChange('testimonials', items); }} placeholder="Cita" />
                    <div className="grid md:grid-cols-3 gap-3">
                      <TextInput value={item.author || ''} onChange={v => { const it = { ...item, author: v }; const items = [...data.testimonials.items]; items[idx] = it; handleItemsChange('testimonials', items); }} placeholder="Autor" />
                      <TextInput value={item.role || ''} onChange={v => { const it = { ...item, role: v }; const items = [...data.testimonials.items]; items[idx] = it; handleItemsChange('testimonials', items); }} placeholder="Rol" />
                      <TextInput value={item.company || ''} onChange={v => { const it = { ...item, company: v }; const items = [...data.testimonials.items]; items[idx] = it; handleItemsChange('testimonials', items); }} placeholder="Compañía" />
                    </div>
                    <button onClick={() => removeItem('testimonials', idx)} className="mt-2 text-red-400 hover:text-red-300 text-sm">Eliminar</button>
                  </div>
                ))}
              </div>
              <button onClick={() => addItem('testimonials', { quote: '', author: '', role: '', company: '' })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Testimonio</button>
            </div>
          )}

          {activeTab === 'stats' && (
            <div>
              <SectionHeader icon={Star} title="Estadísticas" section="stats"/>
              <div className="space-y-3">
                {(data.stats.items || []).map((item, idx) => (
                  <div key={idx} className="p-4 bg-gray-800 border border-gray-700 rounded-xl grid md:grid-cols-3 gap-3">
                    <TextInput value={item.value || ''} onChange={v => { const it = { ...item, value: v }; const items = [...data.stats.items]; items[idx] = it; handleItemsChange('stats', items); }} placeholder="Valor (10K+)" />
                    <TextInput value={item.label || ''} onChange={v => { const it = { ...item, label: v }; const items = [...data.stats.items]; items[idx] = it; handleItemsChange('stats', items); }} placeholder="Etiqueta" />
                    <button onClick={() => removeItem('stats', idx)} className="text-red-400 hover:text-red-300 text-sm">Eliminar</button>
                  </div>
                ))}
              </div>
              <button onClick={() => addItem('stats', { value: '', label: '' })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Estadística</button>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div>
              <SectionHeader icon={Puzzle} title="Integraciones" section="integrations"/>
              <div className="space-y-3">
                {(data.integrations.items || []).map((item, idx) => (
                  <div key={idx} className="p-4 bg-gray-800 border border-gray-700 rounded-xl grid md:grid-cols-3 gap-3">
                    <TextInput value={item.name || ''} onChange={v => { const it = { ...item, name: v }; const items = [...data.integrations.items]; items[idx] = it; handleItemsChange('integrations', items); }} placeholder="Nombre" />
                    <TextInput value={item.icon || ''} onChange={v => { const it = { ...item, icon: v }; const items = [...data.integrations.items]; items[idx] = it; handleItemsChange('integrations', items); }} placeholder="Icono (emoji)" />
                    <button onClick={() => removeItem('integrations', idx)} className="text-red-400 hover:text-red-300 text-sm">Eliminar</button>
                  </div>
                ))}
              </div>
              <button onClick={() => addItem('integrations', { name: '', icon: '' })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Integración</button>
            </div>
          )}

          {activeTab === 'capabilities' && (
            <div>
              <SectionHeader icon={Globe} title="Capacidades" section="capabilities"/>
              <div className="space-y-3">
                {(data.capabilities.items || []).map((item, idx) => (
                  <div key={idx} className="p-4 bg-gray-800 border border-gray-700 rounded-xl grid md:grid-cols-3 gap-3">
                    <TextInput value={item.title || ''} onChange={v => { const it = { ...item, title: v }; const items = [...data.capabilities.items]; items[idx] = it; handleItemsChange('capabilities', items); }} placeholder="Título" />
                    <TextInput value={item.description || ''} onChange={v => { const it = { ...item, description: v }; const items = [...data.capabilities.items]; items[idx] = it; handleItemsChange('capabilities', items); }} placeholder="Descripción" />
                    <button onClick={() => removeItem('capabilities', idx)} className="text-red-400 hover:text-red-300 text-sm">Eliminar</button>
                  </div>
                ))}
              </div>
              <button onClick={() => addItem('capabilities', { title: '', description: '' })} className="mt-4 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Añadir Capacidad</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
