'use client'

import { useCallback, useRef, useEffect, useState } from 'react'
import type { Genre } from '@/lib/types'

const MUSIC_URLS: Record<string, string> = {
  fantasy_kingdom: '/audio/ebunny-medieval-kingdom-loop-366815.mp3',
  outer_space: '/audio/monume-space-509492.mp3',
  underwater_world: '/audio/sonican-optimistic-world-music-loop-530535.mp3',
  jungle_safari: '/audio/leberch-safari-wildlife-525022.mp3',
  menu: '/audio/sigmamusicart-kids-happy-background-music-401734 (1).mp3',
}

const NORMAL_VOLUME = 0.15
const DUCKED_VOLUME = 0.05

export function useBackgroundMusic(genre: Genre | 'menu' | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const isMutedRef = useRef(false)

  // Stop and destroy the current audio completely
  const destroyAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
      audioRef.current.load()
      audioRef.current = null
    }
    setIsPlaying(false)
  }, [])

  const play = useCallback(() => {
    if (!genre || isMutedRef.current) return
    const url = MUSIC_URLS[genre] || MUSIC_URLS['menu']

    // If already playing the same track, do nothing
    if (audioRef.current && !audioRef.current.paused) {
      return
    }

    // Destroy any existing audio first
    destroyAudio()

    try {
      const audio = new Audio(url)
      audio.loop = true
      audio.volume = NORMAL_VOLUME
      audio.preload = 'auto'
      audioRef.current = audio

      const playPromise = audio.play()
      if (playPromise) {
        playPromise
          .then(() => setIsPlaying(true))
          .catch(() => setIsPlaying(false))
      }
    } catch {
      setIsPlaying(false)
    }
  }, [genre, destroyAudio])

  const stop = useCallback(() => {
    isMutedRef.current = true
    destroyAudio()
  }, [destroyAudio])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
        audioRef.current = null
      }
    }
  }, [])

  // Listen for narration events to duck/unduck
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleNarrationStart = () => {
      if (audioRef.current) audioRef.current.volume = DUCKED_VOLUME
    }
    const handleNarrationEnd = () => {
      if (audioRef.current) audioRef.current.volume = NORMAL_VOLUME
    }

    window.addEventListener('narration-start', handleNarrationStart)
    window.addEventListener('narration-end', handleNarrationEnd)

    return () => {
      window.removeEventListener('narration-start', handleNarrationStart)
      window.removeEventListener('narration-end', handleNarrationEnd)
    }
  }, [])

  return { isPlaying, play, stop, fadeOut: stop, duck: () => {}, unduck: () => {}, setVolume: () => {}, volume: NORMAL_VOLUME }
}
