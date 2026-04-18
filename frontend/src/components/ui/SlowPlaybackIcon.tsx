import slowPlaybackTurtle from '../../assets/icons/slow-play-turtle.svg'

interface SlowPlaybackIconProps {
  className?: string
}

export default function SlowPlaybackIcon({ className = 'slow-playback-icon' }: SlowPlaybackIconProps) {
  return <img src={slowPlaybackTurtle} alt="" aria-hidden="true" className={className} />
}
