import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { FeedWindow, Pond } from '../types'

function nowLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

function plusHoursLocal(hours: number) {
  const d = new Date()
  d.setHours(d.getHours() + hours)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const empty = {
  pondId: 0,
  startAt: nowLocal(),
  endAt: plusHoursLocal(4),
  enabled: true,
}

export default function FeedWindows() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<FeedWindow[]>([])
  const [form, setForm] = useState(empty)
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
          ...form,
          startAt: new Date(form.startAt).toISOString(),
          endAt: new Date(form.endAt).toISOString(),
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function toggle(w: FeedWindow) {
    setError('')
    try {
      await api(`/api/feed-windows/${w.id}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !w.enabled }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该投喂窗口？')) return
    try {
      await api(`/api/feed-windows/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} (${p.species})` : `#${id}`
  }

  return (
    <div>
      <header className="page-header">
        <h1>投喂窗口</h1>
        <p className="muted">
          窗口外禁止投喂；同塘口窗口时间段相交返回 409。窗口内仍须满足溶氧规则。
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          塘口
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
        <button type="submit" className="btn primary">
          新增窗口
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
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{pondLabel(r.pondId)}</td>
                <td>{new Date(r.startAt).toLocaleString()}</td>
                <td>{new Date(r.endAt).toLocaleString()}</td>
                <td>
                  <span className={`badge ${r.enabled ? 'window-open' : 'window-closed'}`}>
                    {r.enabled ? '启用' : '停用'}
                  </span>
                </td>
                <td>
                  <button className="btn ghost" onClick={() => toggle(r)}>
                    {r.enabled ? '停用' : '启用'}
                  </button>{' '}
                  <button className="btn ghost" onClick={() => remove(r.id)}>
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
