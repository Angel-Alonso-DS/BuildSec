import { useState, type FormEvent } from 'react'
import { Activity, ArrowDownRight, ArrowRight, Box, Braces, Check, CheckCircle2, ChevronDown, Circle, CircleAlert, Clock3, Code2, ExternalLink, FileCheck2, FileText, Fingerprint, Layers3, LayoutDashboard, LoaderCircle, LockKeyhole, Play, RefreshCw, Shield, ShieldCheck, Sparkles, Terminal, Workflow } from 'lucide-react'
import { executionApi, type Execution, type ExecutionState } from './api'
import { demoCode, demoExecution } from './demo'

const steps: { state: ExecutionState; label: string; caption: string; icon: typeof Layers3 }[] = [
  { state: 'PLANNING', label: 'Planificación', caption: 'Analiza la solicitud', icon: Layers3 },
  { state: 'RISK_ASSESSMENT', label: 'Análisis de riesgos', caption: 'Identifica riesgos', icon: Shield },
  { state: 'GENERATING', label: 'Generación', caption: 'Construye el código', icon: Braces },
  { state: 'VALIDATING', label: 'Validación', caption: 'Ejecuta comprobaciones', icon: CheckCircle2 },
  { state: 'LEARNING', label: 'Aprendizaje', caption: 'Registra resultados', icon: Sparkles },
]
const labels: Record<ExecutionState, string> = { CREATED: 'Creada', PLANNING: 'Planificando', RISK_ASSESSMENT: 'Analizando riesgos', GENERATING: 'Generando', VALIDATING: 'Validando', LEARNING: 'Aprendiendo', COMPLETED: 'Completada', FAILED: 'Fallida', BLOCKED: 'Bloqueada', CANCELLED: 'Cancelada' }
const terminal = new Set<ExecutionState>(['COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED'])

function App() {
  const [demo, setDemo] = useState(false)
  const [execution, setExecution] = useState<Execution | null>(null)
  const [demoVisible, setDemoVisible] = useState(false)
  const [goal, setGoal] = useState('')
  const [checks, setChecks] = useState('F-01, S-01')
  const [workspace, setWorkspace] = useState('workspace')
  const [revision, setRevision] = useState('HEAD')
  const [lookup, setLookup] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'results' | 'code' | 'evidence'>('results')
  const shown = demo ? (demoVisible ? demoExecution : null) : execution
  const passed = shown?.validation.filter(item => item.status === 'passed').length ?? 0

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (demo) { setDemoVisible(true); return }
    const requiredChecks = checks.split(',').map(c => c.trim()).filter(Boolean)
    if (!goal.trim() || !workspace.trim() || !revision.trim() || !requiredChecks.length || new Set(requiredChecks).size !== requiredChecks.length) { setError('Completa todos los campos y proporciona checks únicos separados por comas.'); return }
    setLoading(true)
    try {
      const result = await executionApi.create({ goal: goal.trim(), requiredChecks, workspace: workspace.trim(), revision: revision.trim() })
      setExecution(result); setLookup(result.id)
    } catch (e) { setError(e instanceof Error ? e.message : 'No fue posible crear la ejecución.') }
    finally { setLoading(false) }
  }

  async function refresh() {
    if (demo || !lookup.trim()) return
    setLoading(true); setError('')
    try { setExecution(await executionApi.get(lookup.trim())) }
    catch (e) { setError(e instanceof Error ? e.message : 'No fue posible consultar la ejecución.') }
    finally { setLoading(false) }
  }

  function toggleDemo() { setDemo(!demo); setError(''); setTab('results'); if (!demo) setDemoVisible(true) }

  return <div className="app-shell min-h-screen text-ink">
    <aside className="sidebar hidden lg:flex">
      <a href="#overview" className="brand"><span className="brand-mark"><ShieldCheck size={21} strokeWidth={2.4}/></span><span>build<span className="text-mint">sec</span><small>BUILD WITH CONFIDENCE</small></span></a>
      <div className="sidebar-section">WORKSPACE</div>
      <nav className="side-nav" aria-label="Navegación principal">
        <a className="nav-active" href="#overview"><LayoutDashboard size={18}/> Dashboard <span className="nav-line"/></a>
        <a href="#pipeline"><Workflow size={18}/> Pipeline</a>
        <a href="#results"><FileCheck2 size={18}/> Resultados</a>
        <a href="#history"><Clock3 size={18}/> Historial</a>
      </nav>
      <div className="sidebar-section mt-10">PROYECTO</div>
      <div className="project-label"><span className="project-icon"><Box size={16}/></span><span>BuildSec MVP<small>Workspace principal</small></span><ChevronDown size={15}/></div>
      <div className="sidebar-bottom"><div className="side-note"><ShieldCheck size={19} className="text-mint"/><div><strong>Seguridad integrada</strong><p>Construye con evidencia en cada etapa.</p></div></div><div className="side-user"><span className="avatar">BS</span><div>Equipo BuildSec<small>Workspace local</small></div><ChevronDown size={15}/></div></div>
    </aside>

    <main className="main-area" id="overview">
      <header className="topbar"><div className="breadcrumb"><span>Workspace</span><span className="slash">/</span><strong>Dashboard</strong></div><div className="flex items-center gap-3"><span className={`mode-indicator ${demo ? 'demo-indicator' : ''}`}><i/>{demo ? 'MODO DEMO' : 'API REAL'}</span><button className="mode-button" onClick={toggleDemo}>{demo ? 'Salir de demo' : 'Probar demo'}</button><span className="top-avatar">BS</span></div></header>
      <div className="page-content">
        {demo && <div className="demo-banner"><Sparkles size={16}/> Modo demostración activo · Los datos mostrados son simulados y no representan ejecuciones reales.</div>}
        <div className="page-heading"><div><div className="eyebrow"><span className="tiny-dot"/> TU ESPACIO DE CONSTRUCCIÓN</div><h1>De idea a API, <span>con confianza.</span></h1><p>Diseña, genera y valida software en un solo lugar.</p></div><div className="heading-tag"><ShieldCheck size={16}/> Seguridad desde el inicio</div></div>

        <div className="main-grid">
          <div className="left-column">
            <section className="card create-card" aria-labelledby="create-title"><div className="section-header"><div className="title-icon green"><Sparkles size={18}/></div><div><div className="section-kicker">COMIENZA A CONSTRUIR</div><h2 id="create-title">¿Qué vamos a crear hoy?</h2></div></div><p className="section-description">Describe tu idea y deja que BuildSec te ayude a llevarla a código.</p>
              <form onSubmit={submit}><label htmlFor="goal" className="field-label">Tu solicitud <span>REQUERIDO</span></label><textarea id="goal" value={goal} onChange={e => setGoal(e.target.value)} placeholder="Ej. Una API REST para gestionar tareas, con autenticación y un endpoint de salud..." rows={4}/>
                <div className="form-bottom"><span><Sparkles size={14}/> Describe qué necesitas y cómo debería funcionar.</span><span>{goal.length} caracteres</span></div>
                {!demo && <div className="advanced-fields"><label>Checks requeridos <input value={checks} onChange={e => setChecks(e.target.value)} placeholder="F-01, S-01"/></label><label>Workspace <input value={workspace} onChange={e => setWorkspace(e.target.value)} /></label><label>Revisión <input value={revision} onChange={e => setRevision(e.target.value)} /></label></div>}
                {error && <div className="error-box" role="alert"><CircleAlert size={16}/>{error}</div>}
                <div className="submit-row"><div className="subtle-line"><LockKeyhole size={14}/> {demo ? 'Sin conexión al backend' : 'Conectado a la API HTTP v1'}</div><button className="primary-button" disabled={loading} type="submit">{loading ? <LoaderCircle className="spin" size={17}/> : <Play size={16} fill="currentColor"/>}{loading ? 'Procesando…' : demo ? 'Ver ejecución demo' : 'Iniciar ejecución'} <ArrowRight size={16}/></button></div>
              </form>
            </section>

            <section className="card pipeline-card" id="pipeline"><div className="card-heading"><div><div className="section-kicker">DEL REQUISITO AL RESULTADO</div><h2>Pipeline de agentes</h2><p>Una vista del recorrido de tu ejecución.</p></div><span className={`status-pill ${shown?.state === 'COMPLETED' ? 'success' : shown && terminal.has(shown.state) ? 'warning' : ''}`}><span className="pill-dot"/>{shown ? labels[shown.state] : 'En espera'}</span></div>
              <div className="pipeline">{steps.map((step, index) => { const Icon = step.icon; const visited = shown?.history.includes(step.state) ?? false; const current = shown?.state === step.state; const lastVisited = shown ? [...shown.history].reverse().find(s => steps.some(x => x.state === s)) : undefined; const stopped = !!shown && ['FAILED', 'BLOCKED', 'CANCELLED'].includes(shown.state) && lastVisited === step.state; return <div className="pipeline-step" key={step.state}><div className={`step-icon ${visited ? 'visited' : ''} ${current ? 'current' : ''} ${stopped ? 'stopped' : ''}`}><Icon size={19}/>{visited && !stopped && !current && <span className="check-mark"><Check size={10}/></span>}</div><strong>{step.label}</strong><small>{stopped ? 'Interrumpido' : current ? 'En curso' : visited ? 'Iniciado' : 'Pendiente'}</small><span className="step-caption">{step.caption}</span>{index < steps.length - 1 && <div className={`step-connector ${visited ? 'connector-active' : ''}`}/>}</div> })}</div>
              <div className="pipeline-footer"><Activity size={15}/>{shown ? `Estado reportado: ${labels[shown.state]} · Intentos: ${shown.attempts}` : 'Inicia una ejecución para ver su progreso aquí.'}<span>{shown?.state === 'COMPLETED' ? '100%' : ' '}</span></div>
            </section>

            <section className="card result-card" id="results"><div className="card-heading"><div><div className="section-kicker">TODO EN UN SOLO LUGAR</div><h2>Resultados de la ejecución</h2><p>Revisa las validaciones y los artefactos disponibles.</p></div><span className="results-icon"><Terminal size={19}/></span></div><div className="tabs" role="tablist"><button role="tab" aria-selected={tab === 'results'} onClick={() => setTab('results')}><FileCheck2 size={15}/> Validaciones</button><button role="tab" aria-selected={tab === 'code'} onClick={() => setTab('code')}><Code2 size={15}/> Código</button><button role="tab" aria-selected={tab === 'evidence'} onClick={() => setTab('evidence')}><Fingerprint size={15}/> Evidencias</button></div>
              {tab === 'results' && (shown?.validation.length ? <div className="result-list">{shown.validation.map((v, i) => <div className="result-item" key={`${v.requirement_id}-${i}`}><span className={`result-icon ${v.status}`} >{v.status === 'passed' ? <Check size={17}/> : <CircleAlert size={17}/>}</span><div><strong>{v.requirement_id}</strong><small>{v.tool || 'Herramienta no indicada'} {v.exit_code !== null ? `· salida ${v.exit_code}` : ''}</small></div><span className={`result-status ${v.status}`}>{v.status}</span></div>)}</div> : <Empty icon={FileCheck2} title="Aún no hay resultados" text="Las validaciones aparecerán aquí cuando estén disponibles."/>)}
              {tab === 'code' && (demo && shown ? <div className="code-block"><div><span>main.py</span><span>SOLO LECTURA · DEMO</span></div><pre>{demoCode}</pre></div> : <Empty icon={Code2} title="Código no disponible" text="La API actual no proporciona un endpoint para consultar el código generado."/>)}
              {tab === 'evidence' && (shown?.validation.some(v => v.evidence_id) ? <div className="result-list">{shown.validation.filter(v => v.evidence_id).map((v, i) => <div className="result-item" key={`${v.evidence_id}-${i}`}><span className="result-icon passed"><Fingerprint size={17}/></span><div><strong>{v.evidence_id}</strong><small>{v.requirement_id} · Referencia de evidencia{demo ? ' simulada' : ''}</small></div><span className="muted-label">Solo referencia</span></div>)}</div> : <Empty icon={Fingerprint} title="Sin evidencias disponibles" text="La API actual solo devuelve referencias cuando están disponibles."/>)}
            </section>
          </div>

          <div className="right-column"><section className="card summary-card"><div className="card-heading compact"><div><div className="section-kicker">DE UN VISTAZO</div><h2>Resumen</h2></div><span className="outline-icon"><Activity size={17}/></span></div><p className="summary-caption">{demo ? 'Datos de demostración' : 'Ejecución seleccionada'}</p><div className="summary-grid"><Metric icon={Layers3} label="Ejecución" value={shown ? '01' : '—'} tone="green"/><Metric icon={CheckCircle2} label="Checks aprobados" value={shown ? String(passed).padStart(2, '0') : '—'} tone="blue"/><Metric icon={ShieldCheck} label="Estado" value={shown ? labels[shown.state] : 'Sin datos'} tone="purple"/><Metric icon={FileText} label="Evidencias" value={shown ? String(shown.validation.filter(v => v.evidence_id).length).padStart(2, '0') : '—'} tone="orange"/></div><div className="summary-foot"><span><i/> {demo ? 'Información simulada' : 'Información de esta sesión'}</span><ArrowDownRight size={15}/></div></section>
            <section className="card history-card" id="history"><div className="card-heading compact"><div><div className="section-kicker">CONTINÚA DONDE LO DEJASTE</div><h2>Actividad reciente</h2></div><Clock3 size={18} className="text-slate"/></div><p className="summary-caption">{demo ? 'Ejemplo de actividad' : 'Ejecución seleccionada en esta sesión'}</p>{shown ? <div className="history-entry"><div className="history-icon"><Code2 size={17}/></div><div className="history-copy"><strong>{shown.goal.description}</strong><small>{shown.id}</small><span className={`status-pill ${shown.state === 'COMPLETED' ? 'success' : 'warning'}`}><span className="pill-dot"/>{labels[shown.state]}</span></div></div> : <div className="history-empty"><Clock3 size={20}/><strong>Sin actividad todavía</strong><span>Tu ejecución aparecerá aquí.</span></div>}
              {!demo && <div className="lookup"><label htmlFor="lookup">Consultar por ID</label><div><input id="lookup" value={lookup} onChange={e => setLookup(e.target.value)} placeholder="ID de ejecución"/><button onClick={refresh} disabled={loading || !lookup.trim()} aria-label="Consultar ejecución"><RefreshCw size={16}/></button></div><small>El backend no ofrece un listado histórico.</small></div>}
            </section>
            <section className="trust-card"><div className="trust-top"><div className="trust-icon"><ShieldCheck size={20}/></div><ExternalLink size={15}/></div><h3>Construye con seguridad</h3><p>La seguridad forma parte del proceso, desde los requisitos hasta la validación.</p><div><span>BUILT FOR TRUST</span><ArrowRight size={16}/></div></section>
          </div>
        </div>
        <footer><span>© BuildSec · Workspace de desarrollo seguro</span><span><span className="footer-dot"/> Monolito modular <span className="footer-divider">·</span> ISO/IEC 27001:2022 como referencia</span></footer>
      </div>
    </main>
  </div>
}

function Empty({ icon: Icon, title, text }: { icon: typeof Circle; title: string; text: string }) { return <div className="empty-state"><span><Icon size={20}/></span><div><strong>{title}</strong><p>{text}</p></div></div> }
function Metric({ icon: Icon, label, value, tone }: { icon: typeof Circle; label: string; value: string; tone: string }) { return <div className="metric"><span className={`metric-icon ${tone}`}><Icon size={16}/></span><strong>{value}</strong><small>{label}</small></div> }

export default App
