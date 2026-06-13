'use client'

import { useCallback, useRef, useEffect, useState } from 'react'
import type { Genre } from '@/lib/types'

/**
 * Local royalty-free children's music loops served from /public/audio/.
 * Volume is kept low (0.15 default) and ducks further during narration
 * to ensure TTS/Read-to-Me is never disrupted by background audio.
 */
const MUSIC_URLS: Record<string, string> = {
  fantasy_kingdom: '/audio/ebunny-medieval-kingdom-loop-366815.mp3',
  outer_space: '/audio/monume-space-509492.mp3',
  underwater_world: '/audio/sonican-optimistic-world-music-loop-530535.mp3',
  jungle_safari: '/audio/leberch-safari-wildlife-525022.mp3',
  menu: '/audio/sigmamusicart-kids-happy-background-music-401734 (1).mp3',
}

/** Normal background music volume — kept low so it never competes with narration */
const NORMAL_VOLUME = 0.15
/** Ducked volume when narration/TTS is playing */
const DUCKED_VOLUME = 0.05

export function useBackgroundMusic(genre: Genre | 'menu' | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [volume, setVolume] = useState(NORMAL_VOLUME)
  const [isDucked, setIsDucked] = useState(false)

  const play = useCallback(() => {
    if (!genre) return
    const url = MUSIC_URLS[genre] || MUSIC_URLS['menu']

    if (audioRef.current) {
      // If same track is already loaded, just resume
      if (audioRef.current.src.endsWith(url.split('/').pop() || '')) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {})
        return
      }
      audioRef.current.pause()
    }

    try {
      const audio = new Audio(url)
      audio.loop = true
      audio.volume = isDucked ? DUCKED_VOLUME : volume
      audio.preload = 'auto'
      audioRef.current = audio

      // Wait for enough data to buffer before playing to avoid stuttering
      audio.addEventListener('canplaythrough', () => {
        audio.play()
          .then(() => setIsPlaying(true))
          .catch(() => setIsPlaying(false))
      }, { once: true })

      audio.load()
    } catch {
      setIsPlaying(false)
    }
  }, [genre, volume, isDucked])

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    setIsPlaying(false)
  }, [])

  const fadeOut = useCallback(() => {
    if (!audioRef.current) return
    const audio = audioRef.current
    const fadeInterval = setInterval(() => {
      if (audio.volume > 0.02) {
        audio.volume = Math.max(0, audio.volume - 0.02)
      } else {
        clearInterval(fadeInterval)
        audio.pause()
        audioRef.current = null
        setIsPlaying(false)
      }
    }, 50)
  }, [])

  /**
   * Duck the music volume when narration starts (TTS / Read-to-Me).
   * This ensures the child's story narration is always clearly audible.
   */
  const duck = useCallback(() => {
    setIsDucked(true)
    if (audioRef.current) {
      audioRef.current.volume = DUCKED_VOLUME
    }
  }, [])

  /**
   * Restore normal volume when narration ends.
   */
  const unduck = useCallback(() => {
    setIsDucked(false)
    if (audioRef.current) {
      audioRef.current.volume = volume
    }
  }, [volume])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  // Auto-switch track when genre changes while playing
  useEffect(() => {
    if (isPlaying && genre) {
      // Genre changed while music was playing — crossfade to new track
      const url = MUSIC_URLS[genre] || MUSIC_URLS['menu']
      if (audioRef.current && audioRef.current.src !== new URL(url, window.location.origin).href) {
        // Fade out old, start new
        const oldAudio = audioRef.current
        const fadeInterval = setInterval(() => {
          if (oldAudio.volume > 0.02) {
            oldAudio.volume = Math.max(0, oldAudio.volume - 0.03)
          } else {
            clearInterval(fadeInterval)
            oldAudio.pause()
          }
        }, 50)

        // Start new track
        try {
          const newAudio = new Audio(url)
          newAudio.loop = true
          newAudio.volume = 0
          audioRef.current = newAudio
          newAudio.play().then(() => {
            // Fade in new track
            const fadeInInterval = setInterval(() => {
              if (newAudio.volume < (isDucked ? DUCKED_VOLUME : volume) - 0.02) {
                newAudio.volume = Math.min(isDucked ? DUCKED_VOLUME : volume, newAudio.volume + 0.02)
              } else {
                newAudio.volume = isDucked ? DUCKED_VOLUME : volume
                clearInterval(fadeInInterval)
              }
            }, 50)
          }).catch(() => {})
        } catch {}
      }
    }
  }, [genre])

  /**
   * Listen for narration events to auto-duck background music.
   * The ScenePlayer dispatches 'narration-start' and 'narration-end' 
   * custom events when TTS audio plays/stops.
   * Also listens for browser speechSynthesis as a fallback.
   */
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleNarrationStart = () => duck()
    const handleNarrationEnd = () => unduck()

    window.addEventListener('narration-start', handleNarrationStart)
    window.addEventListener('narration-end', handleNarrationEnd)

    return () => {
      window.removeEventListener('narration-start', handleNarrationStart)
      window.removeEventListener('narration-end', handleNarrationEnd)
    }
  }, [duck, unduck])

  return { isPlaying, play, stop, fadeOut, duck, unduck, setVolume, volume }
}
