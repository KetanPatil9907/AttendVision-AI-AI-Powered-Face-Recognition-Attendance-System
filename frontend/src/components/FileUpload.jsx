import { useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import { cx } from './ui.jsx'

export default function FileUpload({
  onSelect,
  loading,
  compact,
  multiple = false,
  maxFiles = 1,
  hint = 'JPG / PNG, max 10 MB',
  disabled = false,
  label = 'Upload photo',
}) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (fileList) => {
    if (disabled || loading || !fileList?.length) return
    const files = Array.from(fileList).slice(0, multiple ? maxFiles : 1)
    onSelect(multiple ? files : files[0])
  }

  return (
    <div
      role="button"
      tabIndex={disabled || loading ? -1 : 0}
      aria-label={label}
      onClick={() => !disabled && !loading && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          if (!disabled && !loading) inputRef.current?.click()
        }
      }}
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        handleFiles(e.dataTransfer.files)
      }}
      className={cx(
        'flex flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-200',
        disabled || loading
          ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-70'
          : 'cursor-pointer',
        dragOver
          ? 'border-brand-500 bg-brand-50'
          : !disabled && !loading
            ? 'border-slate-300 bg-slate-50 hover:border-brand-400 hover:bg-brand-50/40'
            : '',
        compact ? 'gap-1 p-4 text-center' : 'gap-2 p-8 text-center',
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple={multiple}
        className="sr-only"
        disabled={disabled || loading}
        onChange={(e) => {
          handleFiles(e.target.files)
          // Allow re-selecting the same file after a rejection.
          e.target.value = ''
        }}
      />
      <UploadCloud className={cx('text-brand-500', compact ? 'h-6 w-6' : 'h-8 w-8')} aria-hidden="true" />
      <p className={cx('text-slate-600', compact ? 'text-xs' : 'text-sm')}>
        {loading ? 'Uploading…' : 'Click to upload or drag & drop'}
      </p>
      <p className={cx('text-slate-400', compact ? 'text-[10px]' : 'text-xs')}>{hint}</p>
    </div>
  )
}