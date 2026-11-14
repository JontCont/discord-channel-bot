import Editor, { type OnMount } from '@monaco-editor/react'
import { Code2, Plus, Sparkles, Table2, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type RoleRow = [number, string, number]

function intToHex(color: number): string {
  const clamped = Math.max(0, Math.min(0xffffff, Math.trunc(color) || 0))
  return `#${clamped.toString(16).padStart(6, '0').toUpperCase()}`
}

function hexToInt(hex: string): number {
  const cleaned = hex.replace(/^#/, '')
  const parsed = Number.parseInt(cleaned, 16)
  return Number.isNaN(parsed) ? 0 : parsed
}

function tryParseRoles(value: string): RoleRow[] | null {
  try {
    const parsed = JSON.parse(value) as unknown
    if (!Array.isArray(parsed)) return null
    const rows: RoleRow[] = []
    for (const item of parsed) {
      if (
        Array.isArray(item) &&
        item.length === 3 &&
        typeof item[0] === 'number' &&
        typeof item[1] === 'string' &&
        typeof item[2] === 'number'
      ) {
        rows.push([item[0], item[1], item[2]])
      } else {
        return null
      }
    }
    return rows
  } catch {
    return null
  }
}

function serializeRoles(rows: RoleRow[]): string {
  return `[\n${rows.map((row) => `  ${JSON.stringify(row)}`).join(',\n')}\n]`
}

type LevelRolesEditorProps = {
  value: string
  onChange: (next: string) => void
}

export function LevelRolesEditor({ value, onChange }: LevelRolesEditorProps) {
  const [mode, setMode] = useState<'code' | 'visual'>('code')
  const [isDark, setIsDark] = useState(
    () => document.documentElement.dataset.theme === 'dark',
  )

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.dataset.theme === 'dark')
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
    return () => observer.disconnect()
  }, [])

  const parsedRows = useMemo(() => tryParseRoles(value), [value])

  const handleEditorMount: OnMount = (_editor, monaco) => {
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      allowComments: false,
      schemas: [
        {
          uri: 'https://channel-bot.local/schemas/level-roles.json',
          fileMatch: ['*'],
          schema: {
            type: 'array',
            description: '等級里程碑身分組清單：[[等級, "身分組名稱", 十進位色碼], ...]',
            minItems: 1,
            items: {
              type: 'array',
              minItems: 3,
              maxItems: 3,
              items: [
                {
                  type: 'integer',
                  minimum: 1,
                  description: '目標等級（正整數，需由小到大排列）',
                },
                {
                  type: 'string',
                  minLength: 1,
                  description: 'Discord 身分組名稱（不可重複）',
                },
                {
                  type: 'integer',
                  minimum: 0,
                  maximum: 16777215,
                  description: '十進位 RGB 色碼（0 ~ 16777215，例如 #3498DB = 3447003）',
                },
              ],
            },
          },
        },
      ],
    })
  }

  const updateRow = (index: number, nextRow: RoleRow) => {
    if (!parsedRows) return
    const copy = parsedRows.map((row, idx) => (idx === index ? nextRow : row))
    onChange(serializeRoles(copy))
  }

  const addRow = () => {
    const current = parsedRows ?? []
    const lastLevel = current.length > 0 ? current[current.length - 1]![0] : 0
    const next: RoleRow[] = [...current, [lastLevel + 5, `🌱 湯友 LV${lastLevel + 5}`, 0x3498db]]
    onChange(serializeRoles(next))
  }

  const removeRow = (index: number) => {
    if (!parsedRows || parsedRows.length <= 1) return
    const next = parsedRows.filter((_, idx) => idx !== index)
    onChange(serializeRoles(next))
  }

  const formatJson = () => {
    if (parsedRows) {
      onChange(serializeRoles(parsedRows))
      return
    }
    try {
      const parsed = JSON.parse(value) as unknown
      onChange(JSON.stringify(parsed, null, 2))
    } catch {
      // ignore invalid JSON when formatting
    }
  }

  return (
    <div className="vscode-editor-card">
      <div className="vscode-toolbar">
        <div className="vscode-tabs">
          <button
            type="button"
            className="vscode-tab"
            aria-selected={mode === 'code'}
            onClick={() => setMode('code')}
          >
            <Code2 aria-hidden="true" />
            <span>level_roles.json (VS Code)</span>
          </button>
          <button
            type="button"
            className="vscode-tab"
            aria-selected={mode === 'visual'}
            disabled={!parsedRows}
            title={!parsedRows ? '請先修正 JSON 語法錯誤後再切換至表格模式' : undefined}
            onClick={() => setMode('visual')}
          >
            <Table2 aria-hidden="true" />
            <span>視覺化表格 ({parsedRows?.length ?? 0})</span>
          </button>
        </div>
        <div className="vscode-actions">
          {mode === 'code' && (
            <button
              type="button"
              className="vscode-action-btn"
              onClick={formatJson}
              disabled={!parsedRows}
            >
              <Sparkles aria-hidden="true" />
              <span>格式化</span>
            </button>
          )}
          <button
            type="button"
            className="vscode-action-btn"
            onClick={addRow}
            disabled={!parsedRows}
          >
            <Plus aria-hidden="true" />
            <span>新增列</span>
          </button>
        </div>
      </div>

      {mode === 'code' ? (
        <div className="vscode-monaco-wrap">
          <Editor
            height="240px"
            defaultLanguage="json"
            path="level_roles.json"
            theme={isDark ? 'vs-dark' : 'light'}
            value={value}
            onChange={(nextValue) => onChange(nextValue ?? '')}
            onMount={handleEditorMount}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              fontFamily: "'IBM Plex Mono', Consolas, monospace",
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 2,
              formatOnPaste: true,
              renderLineHighlight: 'all',
              bracketPairColorization: { enabled: true },
              padding: { top: 10, bottom: 10 },
            }}
          />
        </div>
      ) : (
        <div className="vscode-visual-table">
          <div className="vscode-visual-header">
            <span>等級 (LV)</span>
            <span>身分組名稱</span>
            <span>色碼預覽 (點擊選色)</span>
            <span>十進位色碼</span>
            <span />
          </div>
          {parsedRows?.map(([lv, roleName, colorInt], idx) => {
            const hex = intToHex(colorInt)
            return (
              <div key={idx} className="vscode-visual-row">
                <input
                  type="number"
                  min={1}
                  value={lv}
                  onChange={(e) =>
                    updateRow(idx, [Number.parseInt(e.target.value, 10) || 1, roleName, colorInt])
                  }
                />
                <input
                  type="text"
                  value={roleName}
                  onChange={(e) => updateRow(idx, [lv, e.target.value, colorInt])}
                />
                <label className="color-picker-cell">
                  <input
                    type="color"
                    value={hex}
                    onChange={(e) => updateRow(idx, [lv, roleName, hexToInt(e.target.value)])}
                  />
                  <span className="color-hex-code">{hex}</span>
                </label>
                <input
                  type="number"
                  min={0}
                  max={16777215}
                  className="code-input"
                  value={colorInt}
                  onChange={(e) =>
                    updateRow(idx, [lv, roleName, Number.parseInt(e.target.value, 10) || 0])
                  }
                />
                <button
                  type="button"
                  className="icon-button"
                  disabled={parsedRows.length <= 1}
                  title="刪除此列"
                  onClick={() => removeRow(idx)}
                >
                  <Trash2 aria-hidden="true" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {parsedRows && parsedRows.length > 0 && (
        <div className="vscode-role-preview-bar">
          <span className="preview-bar-label">Discord 身分組預覽（點色票可直接改色）：</span>
          <div className="preview-role-chips">
            {parsedRows.map(([lv, roleName, colorInt], idx) => {
              const hex = intToHex(colorInt)
              return (
                <label key={idx} className="discord-role-chip" title={`LV${lv} · ${hex} (${colorInt})`}>
                  <input
                    type="color"
                    value={hex}
                    onChange={(e) => updateRow(idx, [lv, roleName, hexToInt(e.target.value)])}
                  />
                  <span className="role-dot" style={{ background: hex }} />
                  <span className="role-chip-lv">LV{lv}</span>
                  <span className="role-chip-name">{roleName}</span>
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
