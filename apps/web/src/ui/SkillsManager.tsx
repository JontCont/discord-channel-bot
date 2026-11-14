import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  Copy,
  KeyRound,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Users,
} from 'lucide-react'
import { useState } from 'react'
import {
  createGuildSkill,
  deleteGuildSkill,
  getGuildSkills,
  regenerateGuildSkillCode,
  type GuildSkill,
} from '../api'

type SkillsManagerProps = {
  guildId: string
  skillPrefix: string
  directJoinText: string
  onChangeDirectJoinText: (next: string) => void
}

export function SkillsManager({
  guildId,
  skillPrefix,
  directJoinText,
  onChangeDirectJoinText,
}: SkillsManagerProps) {
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [newEmoji, setNewEmoji] = useState('')
  const [addToDirectJoin, setAddToDirectJoin] = useState(true)
  const [copiedSkill, setCopiedSkill] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [regeneratingName, setRegeneratingName] = useState<string | null>(null)

  const skillsQuery = useQuery({
    queryKey: ['guild-skills', guildId],
    queryFn: () => getGuildSkills(guildId),
  })

  const directJoinList = directJoinText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  const directJoinSet = new Set(directJoinList)

  const toggleDirectJoin = (skillName: string) => {
    const next = directJoinSet.has(skillName)
      ? directJoinList.filter((item) => item !== skillName)
      : [...directJoinList, skillName]
    onChangeDirectJoinText(next.join('\n'))
  }

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; emoji?: string }) =>
      createGuildSkill(guildId, payload),
    onSuccess: (created) => {
      queryClient.setQueryData<GuildSkill[]>(['guild-skills', guildId], (prev = []) => [
        ...prev,
        created,
      ])
      if (addToDirectJoin && !directJoinSet.has(created.name)) {
        onChangeDirectJoinText([...directJoinList, created.name].join('\n'))
      }
      setNewName('')
      setNewEmoji('')
    },
  })

  const regenMutation = useMutation({
    mutationFn: async (skillName: string) => {
      setRegeneratingName(skillName)
      try {
        const code = await regenerateGuildSkillCode(guildId, skillName)
        return { skillName, code }
      } finally {
        setRegeneratingName(null)
      }
    },
    onSuccess: ({ skillName, code }) => {
      queryClient.setQueryData<GuildSkill[]>(['guild-skills', guildId], (prev = []) =>
        prev.map((skill) =>
          skill.name === skillName ? { ...skill, invite_code: code } : skill,
        ),
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (skillName: string) => {
      await deleteGuildSkill(guildId, skillName)
      return skillName
    },
    onSuccess: (deletedName) => {
      queryClient.setQueryData<GuildSkill[]>(['guild-skills', guildId], (prev = []) =>
        prev.filter((skill) => skill.name !== deletedName),
      )
      if (directJoinSet.has(deletedName)) {
        onChangeDirectJoinText(
          directJoinList.filter((item) => item !== deletedName).join('\n'),
        )
      }
      setConfirmDelete(null)
    },
  })

  const handleCreate = () => {
    const trimmed = newName.trim()
    if (!trimmed || createMutation.isPending) return
    createMutation.mutate({
      name: trimmed,
      emoji: newEmoji.trim() || undefined,
    })
  }

  const handleCopyCode = async (skillName: string, code: string) => {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedSkill(skillName)
      window.setTimeout(() => {
        setCopiedSkill((curr) => (curr === skillName ? null : curr))
      }, 1800)
    } catch {
      // Clipboard API fallback ignored
    }
  }

  const skills = skillsQuery.data ?? []

  return (
    <div className="skills-manager">
      {/* 建立新湯技區塊 */}
      <div className="skill-create-card">
        <div className="skill-create-header">
          <Sparkles aria-hidden="true" />
          <div>
            <h3>建立新湯技（管理員 `/skill create`）</h3>
            <p>
              建立後會自動在伺服器產生專屬身分組、分類、論壇（討論）、文字（聊天）、語音觸發頻道與 8 碼邀請碼。一般成員可在面板按鈕或使用{' '}
              <code>/skill join &lt;邀請碼&gt;</code> 加入。
            </p>
          </div>
        </div>

        <div className="skill-create-controls">
          <label className="skill-create-field">
            <span>湯技名稱</span>
            <input
              type="text"
              placeholder="例如：音樂術、程式術（不含空白）"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCreate()
                }
              }}
            />
          </label>
          <label className="skill-create-field emoji-field">
            <span>Emoji 圖示（選填）</span>
            <input
              type="text"
              placeholder="🎵"
              maxLength={8}
              value={newEmoji}
              onChange={(e) => setNewEmoji(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCreate()
                }
              }}
            />
          </label>
          <button
            type="button"
            className="button primary skill-create-btn"
            disabled={!newName.trim() || createMutation.isPending}
            onClick={handleCreate}
          >
            {createMutation.isPending ? (
              <Loader2 className="spin" aria-hidden="true" />
            ) : (
              <Plus aria-hidden="true" />
            )}
            <span>建立湯技</span>
          </button>
        </div>

        <div className="skill-create-options">
          <label className="skill-checkbox">
            <input
              type="checkbox"
              checked={addToDirectJoin}
              onChange={(e) => setAddToDirectJoin(e.target.checked)}
            />
            <span>建立後自動加入「面板直接加入」清單（不勾選則僅限邀請碼 `/skill join` 加入）</span>
          </label>
          {newName.trim() && (
            <span className="skill-preview-pill">
              預覽分類：{skillPrefix}
              {newName.trim()}
              {newEmoji.trim() ? ` ${newEmoji.trim()}` : ''}
            </span>
          )}
        </div>

        {createMutation.isError && (
          <p className="field-error" role="alert">
            {createMutation.error.message}
          </p>
        )}
      </div>

      {/* 已建立湯技列表 */}
      <div className="skills-list-wrapper">
        <div className="skills-list-toolbar">
          <div className="skills-list-title">
            <h3>已建立湯技列表（{skills.length}）</h3>
            <span>可查看成員人數、複製或重設 `/skill join` 邀請碼，以及切換是否開放面板直接點擊加入</span>
          </div>
          <button
            type="button"
            className="button secondary skills-refresh-btn"
            disabled={skillsQuery.isFetching}
            onClick={() => void skillsQuery.refetch()}
          >
            <RefreshCw className={skillsQuery.isFetching ? 'spin' : ''} aria-hidden="true" />
            <span>重新整理</span>
          </button>
        </div>

        {skillsQuery.isLoading ? (
          <div className="skills-empty-state">
            <Loader2 className="spin" aria-hidden="true" />
            <span>正在載入已建立的湯技...</span>
          </div>
        ) : skillsQuery.isError ? (
          <div className="skills-empty-state error">
            <span>{skillsQuery.error.message}</span>
          </div>
        ) : skills.length === 0 ? (
          <div className="skills-empty-state">
            <span>目前伺服器尚未建立任何湯技。請使用上方表單建立第一個湯技！</span>
          </div>
        ) : (
          <div className="skills-table-container">
            <table className="skills-table">
              <thead>
                <tr>
                  <th>湯技名稱 ／ 分類</th>
                  <th>成員數</th>
                  <th>加入方式（點擊切換）</th>
                  <th>專屬邀請碼（`/skill join`）</th>
                  <th style={{ width: '110px', textAlign: 'right' }}>管理</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((skill) => {
                  const isDirect = directJoinSet.has(skill.name)
                  const isCopied = copiedSkill === skill.name
                  const isConfirmingDelete = confirmDelete === skill.name
                  const isRegenerating = regeneratingName === skill.name

                  return (
                    <tr key={skill.name}>
                      <td>
                        <div className="skill-cell-main">
                          <span className="skill-emoji-badge">{skill.emoji || '🏷️'}</span>
                          <div>
                            <div className="skill-name-text">{skill.name}</div>
                            <div className="skill-sub-meta">
                              分類：<code>{skill.category_name}</code>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="skill-member-pill">
                          <Users aria-hidden="true" />
                          {skill.member_count} 人
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className={`skill-join-mode-btn ${isDirect ? 'is-direct' : 'is-invite'}`}
                          onClick={() => toggleDirectJoin(skill.name)}
                          title="點擊切換「面板按鈕直接加入」或「僅限邀請碼加入」"
                        >
                          {isDirect ? '🟢 面板直接加入' : '🔐 僅限邀請碼'}
                        </button>
                      </td>
                      <td>
                        <div className="skill-invite-cell">
                          <code className="skill-code-badge">
                            <KeyRound aria-hidden="true" />
                            {skill.invite_code || '尚未產生'}
                          </code>
                          {skill.invite_code && (
                            <button
                              type="button"
                              className="skill-icon-action"
                              onClick={() => void handleCopyCode(skill.name, skill.invite_code)}
                              title="複製邀請碼"
                              aria-label={`複製 ${skill.name} 邀請碼`}
                            >
                              {isCopied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
                            </button>
                          )}
                          <button
                            type="button"
                            className="skill-icon-action"
                            disabled={isRegenerating}
                            onClick={() => regenMutation.mutate(skill.name)}
                            title="重新產生邀請碼（舊碼將立即失效）"
                            aria-label={`重設 ${skill.name} 邀請碼`}
                          >
                            <RefreshCw className={isRegenerating ? 'spin' : ''} aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {isConfirmingDelete ? (
                          <div className="skill-delete-confirm">
                            <button
                              type="button"
                              className="skill-confirm-danger"
                              disabled={deleteMutation.isPending}
                              onClick={() => deleteMutation.mutate(skill.name)}
                            >
                              確定刪除
                            </button>
                            <button
                              type="button"
                              className="skill-confirm-cancel"
                              onClick={() => setConfirmDelete(null)}
                            >
                              取消
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="skill-icon-action danger"
                            onClick={() => setConfirmDelete(skill.name)}
                            title="刪除湯技（連同分類、頻道與身分組一併移除）"
                            aria-label={`刪除 ${skill.name}`}
                          >
                            <Trash2 aria-hidden="true" />
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
