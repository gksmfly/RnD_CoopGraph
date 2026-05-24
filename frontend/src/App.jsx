import { useState } from 'react'

const API = 'http://localhost:8000'

const EXAMPLE_QUERIES = [
  'AI 반도체 분야 핵심 협력 클러스터를 알려줘',
  'NPU 분야에서 ETRI가 참여한 과제와 협력 기관은?',
  'PIM 기술을 연구한 대학 기관과 주요 연구 내용은?',
  '온디바이스 AI에서 기업-대학-출연연 협력 구조는?',
]

export default function App() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [answer, setAnswer] = useState('')
  const [processingTime, setProcessingTime] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [graphSrc, setGraphSrc] = useState(`${API}/api/graph`)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setAnswer('')

    try {
      const res = await fetch(`${API}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode }),
      })
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`)
      const data = await res.json()
      setAnswer(data.answer)
      setProcessingTime(data.processing_time)

      // 관련 엔티티가 있으면 highlight 그래프로 교체
      if (data.entities && data.entities.length > 0) {
        const encoded = encodeURIComponent(data.entities.join(','))
        setGraphSrc(`${API}/api/graph/highlight?nodes=${encoded}`)
      }
    } catch (e) {
      setError(`오류: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setQuery('')
    setAnswer('')
    setError('')
    setProcessingTime(null)
    setGraphSrc(`${API}/api/graph`)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* ── 좌측 사이드바 ── */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-gray-900 font-bold text-base leading-tight">
            RnD<br />
            <span className="text-indigo-600">CoopGraph</span>
          </h1>
          <p className="text-xs text-gray-400 mt-1">R&D 협력 그래프 분석</p>
        </div>

        {/* 질의 모드 */}
        <div className="p-4">
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wider font-medium">질의 모드</p>
          {['hybrid', 'local', 'global'].map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm mb-1 transition-colors ${
                mode === m
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              {m === 'hybrid' && '🔀 Hybrid'}
              {m === 'local'  && '🔍 Local'}
              {m === 'global' && '🌐 Global'}
            </button>
          ))}
        </div>

        {/* 초기화 버튼 */}
        {answer && (
          <div className="p-4 mt-auto border-t border-gray-200">
            <button
              onClick={handleReset}
              className="w-full px-3 py-2 text-sm text-gray-500 hover:text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              초기화
            </button>
          </div>
        )}
      </aside>

      {/* ── 중앙 메인 ── */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* 헤더 */}
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3 shadow-sm">
          <span className="text-gray-400 text-sm">모드:</span>
          <span className="bg-indigo-50 text-indigo-600 text-xs px-2 py-0.5 rounded font-medium">{mode}</span>
          {processingTime && (
            <span className="ml-auto text-xs text-gray-400">⏱ {processingTime}초</span>
          )}
        </header>

        {/* 검색창 */}
        <div className="px-6 py-4 border-b border-gray-200 bg-white">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="질문을 입력하세요... (예: AI 반도체 핵심 협력 클러스터는?)"
              className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white text-sm rounded-lg transition-colors font-medium"
            >
              {loading ? '분석 중...' : '검색'}
            </button>
          </div>

          {/* 예시 질문 */}
          <div className="flex gap-2 mt-2 flex-wrap">
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => setQuery(q)}
                className="text-xs text-gray-500 hover:text-indigo-600 bg-gray-100 hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* 답변 영역 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="flex items-center gap-3 text-gray-500">
              <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm">LightRAG가 KG를 탐색하는 중...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm">
              {error}
            </div>
          )}

          {answer && !loading && (
            <div className="space-y-1">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">답변</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
              <pre className="whitespace-pre-wrap text-sm text-gray-800 leading-7 font-sans bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
                {answer}
              </pre>
            </div>
          )}

          {!answer && !loading && !error && (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
              <div className="text-5xl mb-4">🔭</div>
              <p className="text-base text-gray-500">질문을 입력하면 LightRAG가 KG를 탐색합니다</p>
              <p className="text-xs mt-2 text-gray-400">노드 11,215개 · 엣지 19,925개</p>
            </div>
          )}
        </div>
      </main>

      {/* ── 우측 KG 시각화 패널 ── */}
      <aside className="flex-1 flex flex-col border-l border-gray-200 min-w-0">
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
          <span className="text-sm font-medium text-gray-900">KG 시각화</span>
          <span className="text-xs text-gray-400">
            {graphSrc.includes('highlight') ? '질의 관련 노드 강조' : 'Top 300 노드'}
          </span>
        </div>
        <div className="flex-1 bg-gray-50">
          <iframe
            key={graphSrc}
            src={graphSrc}
            className="w-full h-full border-none"
            title="Knowledge Graph"
          />
        </div>
        {/* 범례 */}
        <div className="bg-white border-t border-gray-200 px-4 py-2 flex gap-3 flex-wrap text-xs text-gray-500">
          <span><span className="text-[#4A90D9]">●</span> 기관</span>
          <span><span className="text-[#7ED321]">●</span> 기술분야</span>
          <span><span className="text-[#F5A623]">●</span> 과제</span>
          <span><span className="text-[#BD10E0]">●</span> 연구자</span>
          <span><span className="text-[#D0021B]">●</span> 부처</span>
          <span><span className="text-[#FFD700]">●</span> 질의 관련</span>
        </div>
      </aside>
    </div>
  )
}
