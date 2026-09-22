import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { FeedWindow, Pond } from '../types'

function toLocalInput(iso: Date) {
  const d = new Date(iso)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

function defaultForm(pondId: number) {
  const start = new Date()
  const end = new Date(start.getTime() + 2 * 60 * 60 * 1000)
  return {
    pondId,
    startAt: toLocalInput(start),
    endAt: toLocalInput(end),
    enabled: true,
  }
}

export default function FeedWindows() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<FeedWindow[]>([])
  const [form, setForm] = useState(() => defaultForm(0))
  const [error, setError] = useState('')

  async function load() {
    const [ps, ws] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<FeedWindow[]>('/api/feed-windows'),
    ])
    setPonds(ps)
    setRows(ws)
    if (!form.pondId && ps[0]) {
      setForm((f) => ({ ...f, pondId: ps[0].id }))
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/feed-windows', {
        method: 'POST',
        body: JSON.stringify({
          pondId: form.pondId,
          startAt: new Date(form.startAt).toISOString(),
          endAt: new Date(form.endAt).toISOString(),
          enabled: form.enabled,
        }),
      })
      setForm((f) => ({ ...defaultForm(f.pondId) }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function toggleEnabled(w: FeedWindow) {
    setError('')
    try {
      await api(`/api/feed-windows/${w.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !w.enabled }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该投喂窗口？')) return
    setError('')
    try {
      await api(`/api/feed-windows/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} · ${p.species}` : `#${id}`
  }

  const nowMs = Date.now()
  const stateOf = (w: FeedWindow) => {
    if (!w.enabled) return { text: '已停用', cls: 'badge dry' }
    const start = new Date(w.startAt).getTime()
    const end = new Date(w.endAt).getTime()
    if (nowMs >= start && nowMs <= end) return { text: '开窗中', cls: 'badge stocked' }
    if (nowMs < start) return { text: '未开始', cls: 'badge' }
    return { text: '已结束', cls: 'badge dry' }
  }

  return (
    <div>
      <header className="page-header">
        <h1>投喂窗口</h1>
        <p className="muted">
          同塘口窗口时间不可相交；窗口外投喂返回 409，窗口内还需投喂前 6 小时内有溶氧 ≥ 5 mg/L 的水质样，否则返回 400。
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          所属塘口
          <select
            value={form.pondId}
            onChange={(e) => setForm({ ...form, pondId: Number(e.target.value) })}
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {p.pondCode} · {p.species}
              </option>
            ))}
          </select>
        </label>
        <label>
          是否启用
          <select
            value={form.enabled ? '1' : '0'}
            onChange={(e) => setForm({ ...form, enabled: e.target.value === '1' })}
          >
            <option value="1">启用</option>
            <option value="0">停用</option>
          </select>
        </label>
        <label>
          开始时刻
          <input
            type="datetime-local"
            value={form.startAt}
            onChange={(e) => setForm({ ...form, startAt: e.target.value })}
            required
          />
        </label>
        <label>
          结束时刻
          <input
            type="datetime-local"
            value={form.endAt}
            onChange={(e) => setForm({ ...form, endAt: e.target.value })}
            required
          />
        </label>
        <button type="submit" className="btn primary">
          新建窗口
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>塘口</th>
              <th>开始时刻</th>
              <th>结束时刻</th>
              <th>状态</th>
              <th>启用</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => {
              const st = stateOf(w)
              return (
                <tr key={w.id}>
                  <td>{w.id}</td>
                  <td>{pondLabel(w.pondId)}</td>
                  <td>{new Date(w.startAt).toLocaleString()}</td>
                  <td>{new Date(w.endAt).toLocaleString()}</td>
                  <td>
                    <span className={st.cls}>{st.text}</span>
                  </td>
                  <td>
                    <button className="btn ghost" onClick={() => toggleEnabled(w)}>
                      {w.enabled ? '停用' : '启用'}
                    </button>
                  </td>
                  <td>
                    <button className="btn ghost" onClick={() => remove(w.id)}>
                      删除
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
