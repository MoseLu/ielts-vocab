import { Button, Input, Textarea } from '../../ui'
import { Page, PageContent, PageHeader, PageScroll } from '../../layout'
import { useCreateCustomBookPage } from '../../../composables/books/page/useCreateCustomBookPage'
import {
  CHAPTER_WORD_TARGETS,
  EDUCATION_STAGE_OPTIONS,
  EXAM_TYPE_OPTIONS,
  IELTS_SKILL_OPTIONS,
  countChapterWords,
} from '../create/customBookDraft'

interface Option {
  value: string
  label: string
}

interface OptionGroupProps {
  label: string
  value: string
  options: Option[]
  disabled?: boolean
  onChange: (value: string) => void
}

function OptionGroup({ label, value, options, disabled = false, onChange }: OptionGroupProps) {
  return (
    <div className="custom-book-option-group" aria-disabled={disabled}>
      <span className="custom-book-option-label">{label}</span>
      <div className="custom-book-pills">
        {options.map(option => (
          <button
            type="button"
            key={option.value}
            className={`custom-book-pill${value === option.value ? ' active' : ''}`}
            disabled={disabled}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function CreateCustomBookPage() {
  const page = useCreateCustomBookPage()
  const chapterNumberOffset = page.chapterIndexBase
  const titleLabel = page.isAppendMode ? '继续为词书补充新章节' : '创建一本可立即学习的词书'
  const description = page.isAppendMode
    ? (
        page.isLoadingExistingBook
          ? '正在读取现有词书信息...'
          : `新内容会追加到《${page.title || '当前词书'}》，当前已有 ${page.existingChapterCount} 章、${page.existingWordCount} 个词。`
      )
    : '按章节粘贴单词，或导入 UTF-8 CSV；保存后会加入“我的词书”。'
  const saveLabel = page.isAppendMode ? '保存新增章节' : '保存词书'
  const metaDisabled = page.isAppendMode || page.isLoadingExistingBook

  return (
    <Page className="custom-book-page">
      <PageHeader className="custom-book-header">
        <div className="custom-book-heading">
          <span className="custom-book-kicker">自定义词书</span>
          <h1>{titleLabel}</h1>
          <p>{description}</p>
        </div>
        <div className="custom-book-actions">
          <Button variant="ghost" onClick={page.cancel}>取消</Button>
          <Button onClick={page.saveBook} isLoading={page.isSaving} disabled={page.isLoadingExistingBook}>
            {saveLabel}
          </Button>
        </div>
      </PageHeader>

      <PageContent className="custom-book-content">
        <PageScroll className="custom-book-scroll">
          <section className="custom-book-shell">
            <div className="custom-book-meta-panel">
              <Input
                label="词书名称"
                value={page.title}
                disabled={metaDisabled}
                onChange={event => page.setTitle(event.target.value)}
                placeholder="例如：雅思口语高频短语"
              />

              <div className="custom-book-target-row">
                <div className="custom-book-target-field">
                  <label htmlFor="chapter-word-target">每章单词数</label>
                  <input
                    id="chapter-word-target"
                    type="number"
                    min={1}
                    value={page.chapterWordTarget}
                    disabled={metaDisabled}
                    onChange={event => page.setChapterWordTarget(Math.max(1, Number(event.target.value) || 1))}
                  />
                </div>
                <div className="custom-book-target-presets" aria-label="每章单词数快捷选项">
                  {CHAPTER_WORD_TARGETS.map(target => (
                    <button
                      type="button"
                      key={target}
                      className={page.chapterWordTarget === target ? 'active' : ''}
                      disabled={metaDisabled}
                      onClick={() => page.setChapterWordTarget(target)}
                    >
                      {target}
                    </button>
                  ))}
                </div>
              </div>

              <OptionGroup
                label="词书分类"
                value={page.educationStage}
                options={EDUCATION_STAGE_OPTIONS}
                disabled={metaDisabled}
                onChange={page.setEducationStage}
              />
              <OptionGroup
                label="子分类"
                value={page.examType}
                options={EXAM_TYPE_OPTIONS}
                disabled={metaDisabled}
                onChange={page.setExamType}
              />
              <OptionGroup
                label="雅思分类"
                value={page.ieltsSkill}
                options={IELTS_SKILL_OPTIONS}
                disabled={metaDisabled || page.examType !== 'ielts'}
                onChange={page.setIeltsSkill}
              />

              <label className="custom-book-share-toggle">
                <input
                  type="checkbox"
                  checked={page.shareEnabled}
                  disabled={metaDisabled}
                  onChange={event => page.setShareEnabled(event.target.checked)}
                />
                <span>分享到社区</span>
              </label>
            </div>

            <div className="custom-book-workspace">
              <div className="custom-book-import-bar">
                <div className="custom-book-tabs" aria-label="导入方式">
                  <button
                    type="button"
                    className={page.importMode === 'manual' ? 'active' : ''}
                    onClick={() => page.setImportMode('manual')}
                  >
                    手动章节卡片
                  </button>
                  <button
                    type="button"
                    className={page.importMode === 'csv' ? 'active' : ''}
                    onClick={() => page.setImportMode('csv')}
                  >
                    CSV 导入
                  </button>
                </div>

                <label className="custom-book-file">
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    disabled={page.isLoadingExistingBook}
                    onChange={page.handleCsvFile}
                  />
                  导入 CSV
                </label>
              </div>

              <div className="custom-book-toolbar">
                <div>
                  <strong>{page.chapters.length} 章</strong>
                  <span>{page.totalWords} 个词条</span>
                  {page.csvSummary && <span>{page.csvSummary}</span>}
                </div>
                <div className="custom-book-toolbar-actions">
                  <Button variant="secondary" size="sm" onClick={page.addChapter} disabled={page.isLoadingExistingBook}>
                    添加章节
                  </Button>
                  <Button
                    variant={page.reorderMode ? 'primary' : 'ghost'}
                    size="sm"
                    disabled={page.isLoadingExistingBook}
                    onClick={() => page.setReorderMode(!page.reorderMode)}
                  >
                    {page.reorderMode ? '完成排序' : '调整排序'}
                  </Button>
                </div>
              </div>

              {page.formError && <div className="custom-book-error">{page.formError}</div>}

              <div className={page.reorderMode ? 'custom-book-chapters is-reordering' : 'custom-book-chapters'}>
                {page.chapters.map((chapter, index) => (
                  <article
                    key={chapter.id}
                    className={`custom-book-chapter-card${page.draggedChapterId === chapter.id ? ' dragging' : ''}`}
                    draggable={page.reorderMode}
                    onDragStart={event => page.handleDragStart(chapter.id, event)}
                    onDragOver={page.handleDragOver}
                    onDrop={event => page.handleDrop(chapter.id, event)}
                  >
                    {page.reorderMode ? (
                      <div className="custom-book-chapter-compact">
                        <span className="custom-book-drag-handle">拖拽</span>
                        <div>
                          <strong>{chapter.title || `第${chapterNumberOffset + index + 1}章`}</strong>
                          <span>{countChapterWords(chapter)} 个词</span>
                        </div>
                        <div className="custom-book-reorder-buttons">
                          <button type="button" onClick={() => page.moveChapter(chapter.id, -1)}>上移</button>
                          <button type="button" onClick={() => page.moveChapter(chapter.id, 1)}>下移</button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="custom-book-chapter-header">
                          <Input
                            label={`章节 ${chapterNumberOffset + index + 1}`}
                            value={chapter.title}
                            onChange={event => page.updateChapterTitle(chapter.id, event.target.value)}
                          />
                          <div className="custom-book-chapter-stats">
                            <span>{countChapterWords(chapter)} 个词</span>
                            <button type="button" onClick={() => page.removeChapter(chapter.id)}>删除</button>
                          </div>
                        </div>
                        <Textarea
                          label="单词内容"
                          value={chapter.content}
                          onChange={event => page.updateChapterBody(chapter.id, event.target.value)}
                          placeholder={'一行一个单词或短语\n例如：\nmeticulous\nin the long run\nmake a compelling case'}
                          rows={10}
                        />
                      </>
                    )}
                  </article>
                ))}
              </div>
            </div>
          </section>
        </PageScroll>
      </PageContent>
    </Page>
  )
}
