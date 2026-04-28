import {
  GAME_TEMPLATE_LAYOUTS,
  type GameTemplateLayoutId,
  isGameTemplateDebugLayoutEnabled,
  layoutSlotStyle,
} from './gameTemplateLayout'

function DebugSlots({
  className,
  layoutId,
}: {
  className: string
  layoutId: GameTemplateLayoutId
}) {
  return (
    <div className={className} aria-hidden="true">
      {GAME_TEMPLATE_LAYOUTS[layoutId].slots.map(slot => (
        <span
          key={slot.id}
          className="practice-template-debug__slot practice-template-slot"
          data-layout-slot={slot.id}
          style={layoutSlotStyle(layoutId, slot.id)}
        >
          {slot.id}
        </span>
      ))}
    </div>
  )
}

export function GameTemplateDebugLayer({
  layoutId,
  mobileLayoutId,
}: {
  layoutId: GameTemplateLayoutId
  mobileLayoutId?: GameTemplateLayoutId
}) {
  if (!isGameTemplateDebugLayoutEnabled()) return null

  return (
    <>
      <DebugSlots
        className={`practice-template-debug${mobileLayoutId ? ' practice-template-debug--desktop' : ''}`}
        layoutId={layoutId}
      />
      {mobileLayoutId ? (
        <DebugSlots className="practice-template-debug practice-template-debug--mobile" layoutId={mobileLayoutId} />
      ) : null}
    </>
  )
}
