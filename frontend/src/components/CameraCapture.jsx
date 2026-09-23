import { useEffect, useRef, useState } from 'react'
import { Button, cx } from './ui.jsx'

function cameraErrorMessage(err) {
  const name = err?.name || ''
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
    return 'Camera access was denied. Allow camera permission in your browser and try again.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'No camera was found on this device.'
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'Your camera is busy in another app or tab. Close it and retry.'
  }
  if (err?.message) return err.message
  return 'Could not start the camera.'
}

export default function CameraCapture({ onCapture, capturing, disabled, label = 'Capture & Recognize', compact }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('Camera not available in this browser.')
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 } },
          audio: false,
        })
        if (cancelled) {
          // Unmounted while starting up - never leak the stream.
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
          if (!cancelled) setReady(true)
        }
      } catch (err) {
        if (!cancelled) setError(cameraErrorMessage(err))
      }
    }

    start()
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  const handleCapture = () => {
    const video = videoRef.current
    if (!video?.videoWidth) {
      setError('No video stream available yet.')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    // Draw the frame exactly as displayed (and exactly as a registration photo
    // would look) so embeddings stay comparable with enrolled faces.
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob)
      },
      'image/jpeg',
      0.92,
    )
  }

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-xl bg-black">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          onPlaying={() => setReady(true)}
          className={cx('w-full object-cover', compact ? 'h-48' : 'h-64')}
        />
        {!ready && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-300">
            Starting camera…
          </div>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-amber-600">{error}</p>}
      <Button
        onClick={handleCapture}
        disabled={disabled || capturing || !ready}
        className={cx('w-full', capturing && 'opacity-60')}
      >
        {capturing ? 'Processing…' : label}
      </Button>
    </div>
  )
}
